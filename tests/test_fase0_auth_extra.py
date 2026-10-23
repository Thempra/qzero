"""(fase0/auth) Verificación de proceso real, fuera de pytest.

Estos tests corren un intérprete LIMPIO (subprocess) porque el punto es
demostrar qué hace un despliegue real. Importa que no hereden el opt-out
QZERO_AUTH_ENFORCE=0 que tests/conftest.py declara para el resto de la suite.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_SCRIPT = """
import os, sys
for k in ("ADMIN_PASSWORD", "QZERO_AGENT_TOKEN", "QZERO_REQUIRE_AGENT_TOKEN"):
    os.environ.pop(k, None)
from fastapi.testclient import TestClient
from qzero.api.app import app
c = TestClient(app)
print("pytest_loaded", "pytest" in sys.modules)
print("alerts", c.get("/api/v1/alerts").status_code)
print("health", c.get("/health").status_code)
print("login", c.post("/api/v1/auth/login", json={"password": "x"}).status_code)
"""


def _run(env_extra: dict) -> dict:
    env = dict(os.environ)
    env.pop("PYTEST_CURRENT_TEST", None)
    env.pop("QZERO_AUTH_ENFORCE", None)  # no heredar el opt-out de conftest
    env.update(env_extra)
    env["PYTHONPATH"] = str(REPO / "src")
    out = subprocess.run([sys.executable, "-c", _SCRIPT], cwd=str(REPO),
                         env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    result = {}
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("-").isdigit():
            result[parts[0]] = int(parts[1])
        elif len(parts) == 2:
            result[parts[0]] = parts[1]
    return result


def test_real_process_is_fail_closed_without_password():
    """Sin ADMIN_PASSWORD, un proceso real da 503, nunca 200."""
    r = _run({})
    assert r["pytest_loaded"] == "False"
    assert r["alerts"] == 503
    assert r["login"] == 503
    assert r["health"] == 200  # las exentas siguen respondiendo


def test_real_process_enforce_flag_off_explicitly_opens():
    """QZERO_AUTH_ENFORCE=0 es la única vía de escape, y es explícita."""
    r = _run({"QZERO_AUTH_ENFORCE": "0"})
    assert r["alerts"] != 503


def test_no_sys_modules_sniffing_in_production_code():
    """El código de producción no puede detectar el runner para abrirse.

    Una versión anterior de este parche hacía ``return not ("pytest" in
    sys.modules)``: bastaba que cualquier dependencia importara pytest en el
    proceso para que el auth se abriera solo. Es un backdoor, no una solución.
    """
    src = (REPO / "src/qzero/api/auth.py").read_text(encoding="utf-8")
    # ignorar comentarios: buscamos código ejecutable
    code = "\n".join(line.split("#", 1)[0] for line in src.splitlines())
    assert "sys.modules" not in code, (
        "auth.py inspecciona sys.modules: el enforcement no puede depender "
        "de qué módulos estén importados en el proceso")
    assert "pytest" not in code, (
        "auth.py menciona pytest en código ejecutable: es un backdoor de test")


def test_enforce_default_is_closed_even_under_pytest():
    """Con pytest importado y sin flag, el default sigue siendo cerrado."""
    from qzero.api import auth as auth_mod
    for k in ("QZERO_AUTH_ENFORCE", "ADMIN_PASSWORD"):
        os.environ.pop(k, None)
    try:
        assert auth_mod.auth_enforced() is True
        assert auth_mod.auth_enforce_mode() == "on"
    finally:
        os.environ["QZERO_AUTH_ENFORCE"] = "0"
