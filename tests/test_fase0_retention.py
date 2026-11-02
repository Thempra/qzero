"""Fase 0.5 — retención: purga sin bloquear ingest, VACUUM, digest sin pérdidas.

Estos tests existen porque el batch de implementación entregó el diff de
hub.py/maintenance.py SIN tests. Verifican las tres afirmaciones del diff:
  1. el lock se toma/suelta POR LOTE (el ingest no espera 9 minutos)
  2. purge no encoge el fichero; vacuum sí lo intenta y reporta tamaños
  3. mark_criticals_notified(ids) no marca CRITICAL que no se enviaron
"""

import sqlite3
import threading
import time
from datetime import datetime, timedelta

import pytest

from qzero.api.hub import HubStore


def _make_hub(tmp_path):
    return HubStore(db_path=str(tmp_path / "hub.db"))


def _insert_old(hub, n, days_old=100):
    """Inserta n alertas con timestamp antiguo (fuera de retención)."""
    ts = (datetime.now() - timedelta(days=days_old)).isoformat()
    with hub._lock:
        hub._conn.executemany(
            "INSERT INTO alerts (timestamp, agent_name, src, dst, dst_port,"
            " protocol, severity, anomaly_score)"
            " VALUES (?,?,?,?,?,?,?,?)",
            [(ts, "t", "10.0.0.1", "10.0.0.2", 80, "TCP", "LOW", 1.0)] * n,
        )
        hub._conn.commit()


def _count(hub):
    with hub._lock:
        return hub._conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]


# --- 1) el lock se libera por lote ------------------------------------------

def test_purge_deletes_only_old_rows(tmp_path):
    hub = _make_hub(tmp_path)
    _insert_old(hub, 50, days_old=100)
    # 10 recientes que NO deben borrarse
    ts = datetime.now().isoformat()
    with hub._lock:
        hub._conn.executemany(
            "INSERT INTO alerts (timestamp, agent_name, src, dst, dst_port,"
            " protocol, severity, anomaly_score) VALUES (?,?,?,?,?,?,?,?)",
            [(ts, "t", "1.1.1.1", "2.2.2.2", 443, "TCP", "LOW", 1.0)] * 10,
        )
        hub._conn.commit()

    deleted = hub.purge_old_alerts(retention_days=90)

    assert deleted == 50
    assert _count(hub) == 10


def test_purge_takes_lock_per_batch_not_for_whole_loop(tmp_path, monkeypatch):
    """El punto del fix: el lock se suelta en CADA lote, no al final del barrido.

    El test anterior medía cuánto tardaba un INSERT en conseguir el lock y lo
    comparaba con 500 ms. Eso mide la velocidad del disco del runner, no el
    diseño: en disco lento (CI) el propio DELETE del lote tarda eso y el test
    falla con el código correcto. Aquí se comprueba la propiedad real: durante
    un barrido de N lotes, el lock se libera entre ellos, así que un ingest
    concurrente consigue entrar más de una vez. Con el lock envolviendo el
    `while` entero solo entraría una vez (al terminar).
    """
    hub = _make_hub(tmp_path)
    _insert_old(hub, 3000, days_old=100)

    # Contamos las liberaciones del lock HECHAS POR EL HILO DE LA PURGA:
    # contar todas incluiría las del hilo de ingesta y el test pasaría incluso
    # con el lock único que queremos descartar.
    entradas = {"n": 0}
    original = hub._lock
    hilo_purga = threading.get_ident()

    class _Contador:
        def __enter__(self):
            return original.__enter__()

        def __exit__(self, *exc):
            if threading.get_ident() == hilo_purga:
                entradas["n"] += 1
            return original.__exit__(*exc) or False

        def __getattr__(self, name):
            return getattr(original, name)

    hub._lock = _Contador()

    stop = threading.Event()

    def ingester():
        # El ingest entra al lock; basta con que lo consiga repetidamente.
        while not stop.is_set():
            with hub._lock:
                pass
            time.sleep(0.01)

    th = threading.Thread(target=ingester, daemon=True)
    th.start()
    time.sleep(0.05)
    try:
        borradas = hub.purge_old_alerts(retention_days=90, batch_size=100,
                                        yield_sec=0.001)
    finally:
        stop.set()
        th.join(timeout=5)

    assert borradas == 3000, "la purga no borró las filas viejas"
    # 30 lotes => 30 salidas del lock de la purga (+ las del ingest y el
    # recount). El umbral solo exige que haya más de dos: prueba que no hay
    # un lock único rodeando el barrido completo.
    assert entradas["n"] > 5, (
        f"solo {entradas['n']} liberaciones de lock: el barrido parece estar "
        "bajo un lock único"
    )


def test_purge_with_zero_or_negative_retention_deletes_nothing(tmp_path):
    hub = _make_hub(tmp_path)
    _insert_old(hub, 5, days_old=400)
    assert hub.purge_old_alerts(retention_days=0) == 0
    assert hub.purge_old_alerts(retention_days=-1) == 0
    assert _count(hub) == 5


def test_purge_leaves_consistent_counters(tmp_path):
    hub = _make_hub(tmp_path)
    _insert_old(hub, 40, days_old=100)
    hub.purge_old_alerts(retention_days=90)
    summary = hub.get_summary() if hasattr(hub, "get_summary") else None
    if summary is not None:
        total = summary.get("total_alerts")
        if total is not None:
            assert total == _count(hub)


# --- 2) VACUUM ---------------------------------------------------------------

def test_purge_does_not_shrink_file_but_vacuum_reports_sizes(tmp_path):
    """Documenta el comportamiento real: DELETE no devuelve disco."""
    hub = _make_hub(tmp_path)
    _insert_old(hub, 5000, days_old=100)
    path = tmp_path / "hub.db"
    size_before = path.stat().st_size

    hub.purge_old_alerts(retention_days=90)
    size_after_purge = path.stat().st_size
    assert size_after_purge == size_before  # free pages, no shrink

    result = hub.vacuum()
    assert set(result) >= {"size_before", "size_after", "reclaimed"}
    assert result["size_before"] == size_after_purge
    assert result["size_after"] <= result["size_before"]
    assert result["reclaimed"] == result["size_before"] - result["size_after"]


def test_vacuum_on_empty_db_is_safe(tmp_path):
    hub = _make_hub(tmp_path)
    result = hub.vacuum()
    assert result["size_after"] >= 0


# --- 3) digest de Telegram: no perder CRITICAL fuera del LIMIT ---------------

def test_mark_notified_with_ids_marks_exactly_those(tmp_path):
    hub = _make_hub(tmp_path)
    _insert_old(hub, 60, days_old=1)
    with hub._lock:
        hub._conn.execute("UPDATE alerts SET severity = 'CRITICAL'")
        hub._conn.execute("UPDATE alerts SET notified_telegram = 0")
        hub._conn.commit()

    pending = hub.pop_pending_criticals()
    assert len(pending) == 50  # el LIMIT del digest

    marked = hub.mark_criticals_notified([a["id"] for a in pending])
    assert marked == 50

    with hub._lock:
        left = hub._conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE severity='CRITICAL'"
            " AND notified_telegram = 0"
        ).fetchone()[0]
    # las 10 que no entraron en el digest NO se marcan: siguen pendientes
    assert left == 10, f"se perdieron {10 - left} CRITICAL sin notificar"


def test_mark_notified_without_ids_is_capped_to_digest_window(tmp_path):
    """El camino legacy no puede tragarse un backlog entero."""
    hub = _make_hub(tmp_path)
    _insert_old(hub, 60, days_old=1)
    with hub._lock:
        hub._conn.execute("UPDATE alerts SET severity = 'CRITICAL'")
        hub._conn.execute("UPDATE alerts SET notified_telegram = 0")
        hub._conn.commit()

    marked = hub.mark_criticals_notified()
    assert marked == 50
    with hub._lock:
        left = hub._conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE severity='CRITICAL'"
            " AND notified_telegram = 0"
        ).fetchone()[0]
    assert left == 10


def test_mark_notified_empty_ids_is_noop(tmp_path):
    hub = _make_hub(tmp_path)
    _insert_old(hub, 5, days_old=1)
    with hub._lock:
        hub._conn.execute("UPDATE alerts SET severity = 'CRITICAL'")
        hub._conn.commit()
    assert hub.mark_criticals_notified([]) == 0
