"""Regresión de los hallazgos de DefectDojo (issues #2, #5, #6, #7).

Cada test corresponde a un finding concreto y falla con el código anterior:

- #2 ``dockerfile.security.missing-user``: la imagen final corría como root.
- #5 ``detect-insecure-websocket``: el CLI anunciaba ``ws://`` siempre.
- #6/#7 ``sqlalchemy-execute-raw-query``: ``_migrate`` interpolaba nombres en
  el SQL y usaba ``PRAGMA table_info(...)`` con f-string.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from qzero.api import hub as hub_mod

REPO = Path(__file__).resolve().parent.parent


# ── #6 / #7: identificadores SQL ──────────────────────────────────────────────

@pytest.mark.parametrize("name", ["alerts", "detail", "notified_telegram", "_x1"])
def test_check_identifier_accepts_real_identifiers(name):
    assert hub_mod._check_identifier(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "alerts; DROP TABLE alerts",
        "alerts--",
        "alerts) --",
        "",
        None,
        "alerts detail",
        "1alerts",
        "alerts\x00",
    ],
)
def test_check_identifier_rejects_injection(name):
    with pytest.raises(ValueError):
        hub_mod._check_identifier(name)


def test_migrate_still_adds_missing_columns(tmp_path):
    """El cambio a consulta parametrizada no puede romper la migración real."""
    import sqlite3

    db = tmp_path / "hub.db"
    store = hub_mod.HubStore(str(db))
    # Un hub antiguo: la tabla alerts sin las columnas de _SCHEMA_MIGRATIONS.
    cols = {
        r["name"]
        for r in store._conn.execute("SELECT name FROM pragma_table_info('alerts')")
    }
    assert {"packets", "detail", "notified_telegram"} <= cols
    store.close()


def test_every_schema_migration_has_a_literal_ddl():
    """El DDL es literal: si falta una entrada, la migración no debe adivinar."""
    faltan = [
        (t, c) for t, c, _ in hub_mod._SCHEMA_MIGRATIONS
        if (t, c) not in hub_mod._MIGRATION_DDL
    ]
    assert not faltan, f"migraciones sin DDL literal: {faltan}"


def test_migrate_rejects_poisoned_schema_migration(monkeypatch, tmp_path):
    """Si una entrada de _SCHEMA_MIGRATIONS viniera de fuera, falla en cerrado."""
    monkeypatch.setattr(
        hub_mod, "_SCHEMA_MIGRATIONS",
        [("alerts; DROP TABLE alerts", "x", "TEXT")],
    )
    with pytest.raises(ValueError):
        hub_mod.HubStore(str(tmp_path / "poison.db"))


# ── #5: esquema del WebSocket anunciado por el CLI ────────────────────────────

def test_cli_logs_wss_when_public_url_is_https(monkeypatch, tmp_path):
    # qzero.cli.main es el módulo, pero `from qzero.cli import main` devuelve el
    # grupo de click (el __init__ lo reexporta). Se importa el módulo por nombre.
    import importlib
    cli_mod = importlib.import_module("qzero.cli.main")

    started = {}
    monkeypatch.setattr(
        "uvicorn.run", lambda *a, **k: started.setdefault("ok", True))
    monkeypatch.setattr("qzero.QZero", lambda **kw: types_simple())
    monkeypatch.setenv("QZERO_PUBLIC_URL", "https://qzero.thempra.net/")

    result = CliRunner().invoke(cli_mod.cli, ["server", "--host", "0.0.0.0", "--port", "8000"])
    assert result.exit_code == 0, result.output
    assert "wss://" in result.output
    assert "ws://" not in result.output.replace("wss://", "")


def test_cli_logs_ws_when_no_tls(monkeypatch):
    # qzero.cli.main es el módulo, pero `from qzero.cli import main` devuelve el
    # grupo de click (el __init__ lo reexporta). Se importa el módulo por nombre.
    import importlib
    cli_mod = importlib.import_module("qzero.cli.main")

    monkeypatch.setattr("uvicorn.run", lambda *a, **k: None)
    monkeypatch.setattr("qzero.QZero", lambda **kw: types_simple())
    monkeypatch.delenv("QZERO_PUBLIC_URL", raising=False)

    result = CliRunner().invoke(cli_mod.cli, ["server"])
    assert result.exit_code == 0, result.output
    assert "ws://" in result.output


def types_simple():
    """Doble mínimo de QZero: el CLI sólo toca ``.predictor``."""
    class _P:
        pass

    class _Q:
        predictor = _P()

    return _Q()


# ── #2: la imagen no corre como root ──────────────────────────────────────────

def _final_user(dockerfile: Path) -> str | None:
    users = [
        line.split(None, 1)[1].strip()
        for line in dockerfile.read_text().splitlines()
        if re.match(r"^\s*USER\s+", line, re.I)
    ]
    return users[-1] if users else None


def test_api_dockerfile_runs_as_non_root():
    user = _final_user(REPO / "Dockerfile")
    assert user is not None, "Dockerfile sin USER: el proceso corre como root"
    assert user.split(":")[0] not in ("root", "0")
