"""
Fase 0.6 / 0.7 — regresión del motor de scoring de QZero.

Cubre los dos defectos que hacían inservible la detección:

B-6 (NaN fail-open): ``std = exp(0.5*logvar)`` desbordaba a ``inf`` con
logvar alto; el MSE salía NaN y ``NaN > umbral`` es False, así que TODO flujo
envenenado se etiquetaba 0 = NORMAL.

B-5 (score sin cota + triple escalado): los errores crudos llegan a 1e17
mientras ``alert_threshold`` es 4.2, y el StandardScaler se aplicaba en
detector.py + predict() + get_anomaly_score().
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from qzero.quantum.qivae import (  # noqa: E402
    LOGVAR_CLAMP_MAX,
    LOGVAR_CLAMP_MIN,
    SCORE_SANITIZE_SENTINEL,
    QIVAE,
    QIVAEConfig,
)
from qzero.core.predictor import (  # noqa: E402
    ALERT_SCORE_ANCHOR,
    SCORE_DECADE_GAIN,
    SCORE_MAX,
    normalize_score,
)


# ── (a) logvar enorme no produce inf/NaN ──────────────────────────────────

def _tiny_qivae(input_dim=6, latent_dim=3, epochs=2):
    cfg = QIVAEConfig(
        input_dim=input_dim,
        latent_dim=latent_dim,
        hidden_dims=(16, 8),
        epochs=epochs,
        batch_size=16,
        anomaly_threshold_percentile=85.0,
    )
    return QIVAE(cfg)


def test_logvar_clamp_constants_are_sane():
    assert LOGVAR_CLAMP_MIN == -20.0
    assert LOGVAR_CLAMP_MAX == 20.0
    # exp(0.5*20) = e^10 ~ 22026: holgadamente finito en float32.
    assert np.isfinite(np.exp(0.5 * LOGVAR_CLAMP_MAX))


def test_reconstruction_errors_finite_with_huge_logvar():
    """El encoder saturado (logvar=+942) ya no envenena los errores."""
    qivae = _tiny_qivae()
    X = np.random.default_rng(0).normal(size=(32, 6)).astype(np.float32)
    qivae.fit(X, verbose=False)

    # Forzamos la saturación del head de log-varianza hasta el valor observado
    # en producción (+942).
    with torch.no_grad():
        qivae.model.encoder.fc_logvar.bias.fill_(942.0)
        qivae.model.encoder.fc_logvar.weight.zero_()

    errors = qivae.reconstruction_errors(X)
    assert np.all(np.isfinite(errors)), f"errores no finitos: {errors[:5]}"
    assert errors.shape == (32,)


def test_reparameterize_clamps_logvar_directly():
    """Unidad: reparameterize con logvar=942 no devuelve inf/NaN."""
    qivae = _tiny_qivae()
    X = np.random.default_rng(1).normal(size=(8, 6)).astype(np.float32)
    qivae.fit(X, verbose=False)

    mu = torch.zeros(4, 3)
    logvar = torch.full((4, 3), 942.0)
    z = qivae.model.reparameterize(mu, logvar)
    assert torch.isfinite(z).all(), "reparameterize devolvió inf/NaN"
    # cota: |z| <= exp(0.5*20)*|eps| ≈ 22026 * ~4 sigma, nunca 1e409
    assert z.abs().max().item() < 1e9

    logvar_neg = torch.full((4, 3), -942.0)
    z2 = qivae.model.reparameterize(mu, logvar_neg)
    assert torch.isfinite(z2).all()


# ── (b) NaN -> clasificado como ANOMALÍA (fail-closed) ────────────────────

def test_nan_flow_classified_as_anomaly(monkeypatch):
    qivae = _tiny_qivae()
    X = np.random.default_rng(2).normal(size=(10, 6)).astype(np.float32)
    qivae.fit(X, verbose=False)

    errors = np.full(10, np.nan)
    errors[0] = 0.0  # un flujo claramente normal
    monkeypatch.setattr(qivae, "reconstruction_errors", lambda _X: errors.copy())

    preds = qivae.predict(X)
    assert preds.shape == (10,)
    assert preds[0] == 0, "un error finito bajo el umbral debe seguir siendo normal"
    assert preds[1:].sum() == 9, f"los NaN deben ser anomalía, salió {preds}"


def test_non_finite_errors_sanitized_to_finite_sentinel():
    """reconstruction_errors sanea NaN/inf: el score devuelto es finito."""
    qivae = _tiny_qivae()
    X = np.random.default_rng(3).normal(size=(16, 6)).astype(np.float32)
    qivae.fit(X, verbose=False)

    with torch.no_grad():
        # Peso gigante => activaciones inf => MSE inf/NaN
        qivae.model.encoder.fc_logvar.bias.fill_(1e30)

    errors = qivae.reconstruction_errors(X)
    assert np.all(np.isfinite(errors))
    assert errors.max() <= SCORE_SANITIZE_SENTINEL


# ── (c) normalize_score: monótona y acotada a [0,100] hasta 1e17 ──────────

def test_normalize_score_bounded_and_monotonic():
    raws = [0.0, 1e-30, 1e-3, 1e-1, 0.4824, 1.0, 3.0, 57.8, 1e3, 1e6,
            1e9, 1.9e9, 1e12, 1e15, 1e16, 1.2e17, 1e17]
    scores = [normalize_score(r, reference=1.0) for r in raws]

    assert all(0.0 <= s <= 100.0 for s in scores), scores
    assert scores == sorted(scores), f"no monótona: {scores}"
    assert scores[-1] == pytest.approx(SCORE_MAX, abs=1e-6)
    # extremos exactos
    assert normalize_score(0.0) == 0.0
    assert normalize_score(-5.0) == 0.0


def test_normalize_score_anchor_is_alert_threshold():
    """raw == referencia => exactamente 4.2 (el umbral del agente)."""
    assert normalize_score(1.0, reference=1.0) == pytest.approx(ALERT_SCORE_ANCHOR)
    assert normalize_score(0.4824, reference=0.4824) == pytest.approx(
        ALERT_SCORE_ANCHOR
    )


def test_normalize_score_preserves_relative_order():
    """El orden relativo de los flujos no cambia al normalizar."""
    raw = np.array([1.9e9, 3.4e9, 1.2e17, 0.1, 5.0])
    norm = np.array([normalize_score(v, reference=0.4824) for v in raw])
    assert np.all(np.diff(norm[np.argsort(raw)]) >= 0)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_normalize_score_non_finite_fails_closed(bad):
    assert normalize_score(bad, reference=1.0) == SCORE_MAX


# ── (d) el escalado se aplica UNA sola vez ────────────────────────────────

class _RecordingScaler:
    """Scaler que cuenta invocaciones y aplica una transformación conocida."""

    def __init__(self, n_features=4):
        self.n_features_in_ = n_features
        self.calls = 0

    def transform(self, X):
        self.calls += 1
        return np.asarray(X, dtype=float) * 10.0


class _StubQIVAE:
    def __init__(self, raw_errors):
        self.anomaly_threshold = 0.4824
        self._raw = np.asarray(raw_errors, dtype=float)
        self.seen = None

    def reconstruction_errors(self, X):
        self.seen = np.asarray(X, dtype=float).copy()
        return self._raw.copy()

    def predict(self, X):
        self.seen = np.asarray(X, dtype=float).copy()
        return (self._raw > self.anomaly_threshold).astype(int)


def _predictor_with(stub, scaler):
    from qzero.core.predictor import QZeroPredictor

    p = QZeroPredictor()
    p.model_fitted = True
    p.qivae_model = stub
    p.scaler = scaler
    return p


def test_scaler_applied_exactly_once_in_get_anomaly_score():
    scaler = _RecordingScaler(4)
    stub = _StubQIVAE([1.0, 2.0, 3.0])
    p = _predictor_with(stub, scaler)
    X = np.array([[1.0, 1.0, 1.0, 1.0]] * 3)

    p.get_anomaly_score(X)

    assert scaler.calls == 1, f"el scaler se aplicó {scaler.calls} veces"
    # El modelo debe recibir x*10 (una pasada), no x*100 (dos).
    assert stub.seen == pytest.approx(X * 10.0)


def test_scaler_applied_exactly_once_in_predict():
    scaler = _RecordingScaler(4)
    stub = _StubQIVAE([1.0, 2.0, 3.0])
    p = _predictor_with(stub, scaler)
    X = np.array([[1.0, 1.0, 1.0, 1.0]] * 3)

    p.predict(X, method="qivae")

    assert scaler.calls == 1, f"el scaler se aplicó {scaler.calls} veces"
    assert stub.seen == pytest.approx(X * 10.0)


def test_known_vector_not_double_scaled_end_to_end():
    """Vector conocido: el score reportado corresponde a UNA sola pasada.

    Con scaler x10 y raw=0.4824 (= umbral del modelo) el score normalizado debe
    ser exactamente 4.2. Si el detector pre-transformase además, el raw que
    vería el modelo sería otro y el score no cuadraría.
    """
    scaler = _RecordingScaler(4)
    stub = _StubQIVAE([0.4824])
    p = _predictor_with(stub, scaler)
    X = np.array([[0.5, 0.5, 0.5, 0.5]])

    scores = p.get_anomaly_score(X)

    assert scaler.calls == 1
    assert scores[0] == pytest.approx(ALERT_SCORE_ANCHOR, abs=1e-9)
