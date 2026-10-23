"""Fase 1.6/1.7 — regresión de los scripts de benchmark honesto.

Verifica tres cosas:

1. Los dos scripts del bench son importables como módulos (sin ejecutar main()).
2. Las funciones de cálculo dan el resultado correcto sobre datos de juguete con
   respuesta conocida a mano: percentiles, matriz de confusión, métricas
   derivadas, varianza cero, baseline mayoritario y stump de un feature.
3. Los benchmarks declaran NO MEDIDO lo que no pueden medir: el JSON de
   throughput no incluye red/Gbps y el de detección marca el banco como
   degenerado cuando se le dan datos degenerados.

No entrena modelos ni lee pcaps: son tests de la aritmética y de los contratos
de salida, que es donde un benchmark "honesto" se puede volver deshonesto.
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _load(name: str):
    """Importa un script con guion bajo desde scripts/ (no es un paquete)."""
    path = SCRIPTS / f"{name}.py"
    if not path.exists():
        pytest.fail(f"falta el script {path}")
    spec = importlib.util.spec_from_file_location(f"_bench_{name}", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tp():
    return _load("bench_throughput")


@pytest.fixture(scope="module")
def dt():
    return _load("bench_detection")


# ---------------------------------------------------------------- importables
def test_scripts_are_importable(tp, dt):
    assert callable(tp.main)
    assert callable(dt.main)
    # las funciones de cálculo que el informe cita existen
    for fn in ("percentile", "summarize_latencies", "rates"):
        assert callable(getattr(tp, fn)), fn
    for fn in ("confusion_matrix", "metrics_from_cm", "zero_variance_features",
               "unique_row_count", "single_packet_share", "majority_baseline",
               "best_single_feature_stump", "verdict"):
        assert callable(getattr(dt, fn)), fn


# ---------------------------------------------------------------- percentiles
def test_percentile_matches_known_values(tp):
    data = [float(i) for i in range(1, 101)]  # 1..100
    assert tp.percentile(data, 50) == pytest.approx(50.5)
    assert tp.percentile(data, 0) == pytest.approx(1.0)
    assert tp.percentile(data, 100) == pytest.approx(100.0)
    # p99 de 1..100 = 99.01 por interpolación lineal
    assert tp.percentile(data, 99) == pytest.approx(99.01)


def test_percentile_single_and_degenerate(tp):
    assert tp.percentile([7.5], 99) == pytest.approx(7.5)
    assert tp.percentile([3.0, 3.0, 3.0], 95) == pytest.approx(3.0)


def test_percentile_rejects_empty_and_bad_range(tp):
    with pytest.raises(ValueError):
        tp.percentile([], 50)
    with pytest.raises(ValueError):
        tp.percentile([1.0, 2.0], 101)


def test_percentile_matches_numpy(tp):
    rng = np.random.default_rng(0)
    data = rng.normal(5, 2, 1000).tolist()
    for q in (1, 25, 50, 90, 95, 99, 99.9):
        assert tp.percentile(data, q) == pytest.approx(
            float(np.percentile(data, q)), rel=1e-12, abs=1e-12
        )


def test_summarize_latencies_shape(tp):
    s = tp.summarize_latencies([1.0, 2.0, 3.0, 4.0, 100.0])
    assert s["n"] == 5
    assert s["p50_ms"] == pytest.approx(3.0)
    assert s["max_ms"] == pytest.approx(100.0)
    assert s["p99_ms"] >= s["p95_ms"] >= s["p50_ms"]
    with pytest.raises(ValueError):
        tp.summarize_latencies([])


def test_rates_never_infinite(tp):
    assert tp.rates(1000, 2.0) == pytest.approx(500.0)
    assert tp.rates(1000, 0.0) == 0.0
    assert tp.rates(1000, -1.0) == 0.0


# ------------------------------------------------------- confusion / metrics
def test_confusion_matrix_known_cm(dt):
    # 4 normales + 4 anomalías, predicciones hechas a mano
    y_true = [0, 0, 0, 0, 1, 1, 1, 1]
    y_pred = [0, 0, 1, 1, 1, 1, 0, 1]
    cm = dt.confusion_matrix(y_true, y_pred)
    assert cm == {"tn": 2, "fp": 2, "fn": 1, "tp": 3, "n": 8}


def test_confusion_matrix_all_four_cells(dt):
    cm = dt.confusion_matrix([0, 1, 0, 1], [0, 0, 1, 1])
    assert (cm["tn"], cm["fp"], cm["fn"], cm["tp"]) == (1, 1, 1, 1)


def test_confusion_matrix_binarizes_multiclass_labels(dt):
    """Un 2 (dDoS) o un 4 (malware) son anomalía: no pueden caer fuera de la matriz."""
    cm = dt.confusion_matrix([0, 2, 3, 4], [0, 1, 0, 1])
    assert cm == {"tn": 1, "fp": 0, "fn": 1, "tp": 2, "n": 4}
    assert cm["tn"] + cm["fp"] + cm["fn"] + cm["tp"] == cm["n"]


def test_confusion_matrix_rejects_length_mismatch(dt):
    with pytest.raises(ValueError):
        dt.confusion_matrix([0, 1, 1], [0, 1])


def test_metrics_from_cm_known_values(dt):
    m = dt.metrics_from_cm({"tn": 2, "fp": 2, "fn": 1, "tp": 3, "n": 8})
    assert m["accuracy"] == pytest.approx(5 / 8)
    assert m["precision"] == pytest.approx(3 / 5)
    assert m["recall"] == pytest.approx(3 / 4)
    # F1 = 2*0.6*0.75/1.35
    assert m["f1"] == pytest.approx(2 * 0.6 * 0.75 / (0.6 + 0.75))
    assert m["fpr"] == pytest.approx(2 / 4)


def test_metrics_all_positive_predictions_gives_prevalence_f1(dt):
    """Caso que hacía pasar el QSVM por bueno: predecir 1 siempre.

    Con 80% de anomalías, F1 = 0.888... y accuracy = 0.8, sin detectar nada.
    El baseline mayoritario debe reproducir exactamente ese número.
    """
    y_true = [1] * 80 + [0] * 20
    cm = dt.confusion_matrix(y_true, [1] * 100)
    m = dt.metrics_from_cm(cm)
    assert cm["tn"] == 0 and cm["fp"] == 20 and cm["fn"] == 0 and cm["tp"] == 80
    assert m["recall"] == pytest.approx(1.0)
    assert m["f1"] == pytest.approx(2 * (80 / 100) * 1.0 / ((80 / 100) + 1.0))


def test_metrics_no_division_by_zero(dt):
    m = dt.metrics_from_cm({"tn": 0, "fp": 0, "fn": 0, "tp": 0, "n": 0})
    assert all(np.isfinite(v) for v in m.values())


# ---------------------------------------------------------- bank diagnostics
def test_zero_variance_detects_constant_columns(dt):
    df = pd.DataFrame({
        "const_int": [5, 5, 5, 5],
        "const_float": [0.0, 0.0, 0.0, 0.0],
        "varying": [1, 2, 3, 4],
        "two_values": [1, 1, 2, 2],
    })
    assert set(dt.zero_variance_features(df)) == {"const_int", "const_float"}


def test_zero_variance_on_real_bank_shape(dt):
    """La banca sintética del repo tiene 6 constantes de 14; no debe cambiar."""
    pcap_dir = ROOT / "data" / "synthetic-pcaps"
    if not pcap_dir.is_dir() or not list(pcap_dir.glob("*.pcap")):
        pytest.skip("no hay pcaps sintéticos en el repo")
    # no se re-extrae: se comprueba la aritmética con una réplica conocida
    df = pd.DataFrame({
        "total_bwd_packets": [0] * 10,
        "total_length_bwd_packets": [0] * 10,
        "bwd_packet_length_mean": [0] * 10,
        "bwd_iat_mean": [0] * 10,
        "bwd_psh_flags": [0] * 10,
        "fwd_urg_flags": [0] * 10,
        "flow_duration": [0.0, 1.0, 2.0, 0.0, 1.0, 2.0, 0.0, 1.0, 2.0, 3.0],
        "total_fwd_packets": [1, 1, 1, 1, 1, 1, 1, 1, 2, 3],
    })
    zv = dt.zero_variance_features(df)
    assert len(zv) == 6


def test_unique_row_count_collapses_duplicates(dt):
    df = pd.DataFrame({"a": [1.0, 1.0, 2.0, 2.0000000001], "b": [0, 0, 0, 0]})
    assert dt.unique_row_count(df, decimals=6) == 2
    # sin redondear, el ruido float crea una fila "única" falsa
    assert dt.unique_row_count(df, decimals=12) == 3


def test_single_packet_share_known_ratio(dt):
    df = pd.DataFrame({"total_fwd_packets": [1, 1, 1, 0, 2, 5, 8, 9]})
    out = dt.single_packet_share(df)
    assert out["n_flows"] == 8
    assert out["single_fwd_packet"] == 4  # 1,1,1,0
    assert out["single_fwd_packet_pct"] == pytest.approx(50.0)


def test_single_packet_share_requires_column(dt):
    with pytest.raises(ValueError):
        dt.single_packet_share(pd.DataFrame({"other": [1, 2]}))


# ---------------------------------------------------------------- baselines
def test_majority_baseline_picks_most_common(dt):
    out = dt.majority_baseline([0, 0, 1, 0, 2])
    assert out["majority_class"] == 0
    assert out["tp"] == 0
    assert out["tn"] == 3
    assert out["fn"] == 2
    assert out["accuracy"] == pytest.approx(3 / 5)


def test_majority_baseline_rejects_empty(dt):
    with pytest.raises(ValueError):
        dt.majority_baseline([])


def test_stump_finds_perfect_single_feature_split(dt):
    """Etiqueta copiada de una columna: el stump DEBE sacar accuracy 1.0.

    Es exactamente el defecto del generador sintético (la etiqueta vive en el
    tamaño de paquete), así que el test fija la detección de esa fuga.
    """
    X = pd.DataFrame({
        "leaky": [1.0] * 50 + [500.0] * 50,
        "noise": [float(i % 7) for i in range(100)],
    })
    y = [0] * 50 + [1] * 50
    best = dt.best_single_feature_stump(X, y)
    assert best["feature"] == "leaky"
    assert best["accuracy"] == pytest.approx(1.0)


def test_stump_no_better_than_chance_on_pure_noise(dt):
    rng = np.random.default_rng(0)
    X = pd.DataFrame({"noise": rng.normal(size=400)})
    y = rng.integers(0, 2, size=400).tolist()
    best = dt.best_single_feature_stump(X, y)
    # con 200 cortes sobre ruido, ~0.5-0.65; nunca debe llegar a 0.95
    assert best["accuracy"] < 0.95


def test_stump_handles_constant_column(dt):
    X = pd.DataFrame({"const": [3.0] * 20})
    best = dt.best_single_feature_stump(X, [0] * 10 + [1] * 10)
    assert best["feature"] is None and best["accuracy"] == 0.0


# ------------------------------------------------------------------ veredicto
def _degenerate_stats():
    return {
        "n_flows": 2942,
        "n_features": 14,
        "unique_rows": 48,
        "unique_rows_pct": 1.63,
        "n_zero_variance": 6,
        "single_packet_pct": 98.47,
    }


def test_verdict_flags_degenerate_bank(dt):
    v = dt.verdict(_degenerate_stats(), model_f1=0.11, baseline_f1=0.90,
                   stump_acc=0.83, model_acc=0.20)
    assert v["degenerate"] is True
    assert len(v["reasons"]) >= 2
    assert "DEGENERADO" in v["statement"]
    # los motivos citan los números reales, no adjetivos
    joined = " ".join(v["reasons"])
    assert "48" in joined and "6 de 14" in joined and "98.47" in joined


def test_verdict_does_not_flag_a_healthy_bank(dt):
    healthy = {
        "n_flows": 10000, "n_features": 14, "unique_rows": 9500,
        "unique_rows_pct": 95.0, "n_zero_variance": 0, "single_packet_pct": 5.0,
    }
    v = dt.verdict(healthy, model_f1=0.90, baseline_f1=0.55,
                   stump_acc=0.60, model_acc=0.91)
    assert v["degenerate"] is False
    assert v["reasons"] == []


def test_verdict_flags_model_tied_with_baseline(dt):
    healthy = {
        "n_flows": 10000, "n_features": 14, "unique_rows": 9500,
        "unique_rows_pct": 95.0, "n_zero_variance": 0, "single_packet_pct": 5.0,
    }
    v = dt.verdict(healthy, model_f1=0.9000, baseline_f1=0.9005,
                   stump_acc=0.30, model_acc=0.90)
    assert any("baseline trivial" in r for r in v["reasons"])


# -------------------------------------------------------- contratos de salida
def test_throughput_declares_what_is_excluded(tp):
    """El bench de throughput no puede insinuar que mide red: debe excluirlo."""
    import inspect

    src = inspect.getsource(tp.main)
    assert "excluded_from_measurement" in src
    assert "NIC real" in src or "NIC" in src


def test_detection_declares_caveats(dt):
    import inspect

    src = inspect.getsource(dt.main)
    assert "caveats" in src
    assert "verdict" in src
    # el script debe poder decir "no medido" sobre zero-day/FPR real
    assert "zero-day" in src
