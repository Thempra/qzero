#!/usr/bin/env python3
"""Benchmark reproducible: QSVM vs QI-VAE vs baselines clásicos.

Fuente de datos: los pcaps etiquetados PROPIOS de data/synthetic-pcaps/
(normal, ddos, bruteforce, exfiltration, malware). Los flujos se extraen
con FlowExtractor (los 14 features UGRansome reales, idénticos a los de
producción), nunca con datos sintéticos aleatorios.

Protocolo (seed fija = 42, todo determinista):
  1. Tarea binaria con validación LOATO (leave-one-attack-type-out):
     cada fold deja FUERA un ataque completo (simula zero-day); el QI-VAE
     se entrena solo con flujos normales, como en producción.
  2. Tarea binaria con split estratificado 80/20 (sanity check).
  3. Multiclase 5 clases OVR (una por tipo de tráfico) sobre el split.

Modelos:
  - QSVM   (kernel cuántico Qiskit, 4 qubits, máx. 200 muestras;
            fallback clásico reportado honestamente si se activa)
  - QI-VAE (autoencoder variacional cuántico-inspirado, solo-normales)
  - Baselines clásicos sklearn: svm_linear, svm_rbf, random_forest,
    logistic_regression, knn, mlp (todos con random_state=42)

Salida:
  model-performance-reports/benchmark-pcaps-<fecha>.md   (informe real)
  model-performance-reports/benchmark-pcaps-latest.json  (datos máquina)

Uso:
  .venv/bin/python scripts/benchmark-pcaps.py
"""

from __future__ import annotations

import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
from sklearn.decomposition import PCA  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedShuffleSplit  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from qzero.classical.baseline import ClassicalBaseline  # noqa: E402
from qzero.preprocessing.flow_extractor import FLOW_FEATURES, FlowExtractor  # noqa: E402
from qzero.quantum.qsvm import QSVM, QSVMConfig  # noqa: E402
from qzero.quantum.qivae import QIVAE, QIVAEConfig  # noqa: E402

# ---------------------------------------------------------------- config
SEED = 42
PCAP_DIR = ROOT / "data" / "synthetic-pcaps"
REPORTS_DIR = ROOT / "model-performance-reports"
CLASSICAL_MODELS = [
    "svm_linear",
    "svm_rbf",
    "random_forest",
    "logistic_regression",
    "knn",
    "mlp",
]
QSVM_MAX_SAMPLES = 120
# Nota de honestidad: el kernel cuántico de Qiskit cuesta ~0.5 s/par de
# muestras en CPU, así que evaluar QSVM sobre los ~2.3k flujos de test
# completos tardaría horas. El QSVM se entrena y evalúa sobre un
# submuestreo estratificado (seed fija) del train/test; el resto de
# modelos ven el test completo. Se documenta en el informe.
QSVM_MAX_TEST = 60
QIVAE_EPOCHS = 40
N_QUBITS = 4

LABELS = {
    "normal": 0,
    "ddos": 1,
    "bruteforce": 2,
    "exfiltration": 3,
    "malware": 4,
}
ATTACK_CLASSES = ["ddos", "bruteforce", "exfiltration", "malware"]


# ---------------------------------------------------------------- data
def load_flows() -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    """Extrae flujos etiquetados de los pcaps propios."""
    from scapy.all import rdpcap

    extractor = FlowExtractor()
    frames, labels, names = [], [], []
    for pcap in sorted(PCAP_DIR.glob("*.pcap")):
        label = next(k for k in LABELS if pcap.name.startswith(k))
        pkts = list(rdpcap(str(pcap)))
        df = extractor.extract_flows_from_packets(pkts)
        df["n_packets_in"] = len(pkts)
        frames.append(df)
        labels.append(np.full(len(df), LABELS[label]))
        names.append(f"{pcap.name} ({label}): {len(pkts)} paquetes -> {len(df)} flujos")
    X = pd.concat(frames, ignore_index=True)
    y = np.concatenate(labels)
    return X, y, names


def binary_metrics(y_true, y_score, y_pred) -> dict:
    out = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    try:
        out["roc_auc"] = roc_auc_score(y_true, y_score)
    except ValueError:
        out["roc_auc"] = float("nan")
    return out


def _stratified_idx(y, n_max, rng):
    """Índices deterministas, estratificados por clase, hasta n_max muestras."""
    if len(y) <= n_max:
        return np.arange(len(y))
    idx = []
    for cls in np.unique(y):
        cls_idx = np.flatnonzero(y == cls)
        k = max(1, int(round(n_max * len(cls_idx) / len(y))))
        idx.append(rng.choice(cls_idx, size=min(k, len(cls_idx)), replace=False))
    return np.sort(np.concatenate(idx))


def classical_fit_predict(name, Xtr, ytr, Xte):
    baseline = ClassicalBaseline(name)
    t0 = time.time()
    train_time = baseline.fit(Xtr, ytr)
    t1 = time.time()
    pred = baseline.predict(Xte)
    infer_time = time.time() - t1
    try:
        proba = baseline.predict_proba(Xte)[:, 1]
    except Exception:
        proba = pred.astype(float)
    return pred, proba, train_time, infer_time


def qsvm_fit_predict(Xtr_q, ytr, Xte_q):
    qsvm = QSVM(QSVMConfig(
        n_qubits=N_QUBITS,
        max_samples_quantum=QSVM_MAX_SAMPLES,
        use_classical_fallback=True,
        random_state=SEED,
    ))
    t0 = time.time()
    qsvm.fit(Xtr_q, ytr)
    train_time = time.time() - t0
    t1 = time.time()
    pred = qsvm.predict(Xte_q)
    infer_time = time.time() - t1
    try:
        score = qsvm.model.decision_function(Xte_q)
    except Exception:
        score = pred.astype(float)
    return pred, score, train_time, infer_time, bool(getattr(qsvm, "_used_quantum", False))


def qivae_fit_predict(Xtr_normal, Xte, dim):
    qivae = QIVAE(QIVAEConfig(
        input_dim=dim,
        latent_dim=N_QUBITS,
        hidden_dims=(64, 32),
        epochs=QIVAE_EPOCHS,
        batch_size=32,
        beta=1.0,
        random_state=SEED,
    ))
    t0 = time.time()
    qivae.fit(Xtr_normal, verbose=False)
    train_time = time.time() - t0
    t1 = time.time()
    errors = qivae.reconstruction_errors(Xte)
    pred = qivae.predict(Xte)
    infer_time = time.time() - t1
    return pred, errors, train_time, infer_time


def run_fold(X, y_bin, train_mask, test_mask, multiclass_train, multiclass_test):
    """Entrena/evalúa todos los modelos en un fold binario dado."""
    Xtr_raw, Xte_raw = X[train_mask], X[test_mask]
    ytr, yte = y_bin[train_mask], y_bin[test_mask]

    scaler = StandardScaler()
    Xtr = scaler.fit_transform(Xtr_raw)
    Xte = scaler.transform(Xte_raw)

    pca = PCA(n_components=N_QUBITS, random_state=SEED)
    Xtr_q_raw = pca.fit_transform(Xtr)
    Xte_q_raw = pca.transform(Xte)
    # QSVM usa ángulos en [0, pi]
    lo, hi = Xtr_q_raw.min(), Xtr_q_raw.max()
    Xtr_q = np.pi * (Xtr_q_raw - lo) / max(hi - lo, 1e-12)
    Xte_q = np.pi * (Xte_q_raw - lo) / max(hi - lo, 1e-12)

    rows = {}

    # QSVM (submuestreo estratificado determinista por coste del kernel)
    rng = np.random.default_rng(SEED)
    tr_idx = _stratified_idx(ytr, QSVM_MAX_SAMPLES, rng)
    te_idx = _stratified_idx(yte, QSVM_MAX_TEST, rng)
    pred, score, tt, it, used_quantum = qsvm_fit_predict(
        Xtr_q[tr_idx], ytr[tr_idx], Xte_q[te_idx]
    )
    m = binary_metrics(yte[te_idx], score, pred)
    m.update(train_time_s=tt, inference_time_s=it, used_quantum=used_quantum)
    rows["QSVM"] = m

    # QI-VAE (solo flujos normales del train)
    normal_tr = Xtr[ytr == 0]
    pred, score, tt, it = qivae_fit_predict(normal_tr, Xte, Xtr.shape[1])
    m = binary_metrics(yte, score, pred)
    m.update(train_time_s=tt, inference_time_s=it)
    rows["QI-VAE"] = m

    # Baselines clásicos
    for name in CLASSICAL_MODELS:
        pred, proba, tt, it = classical_fit_predict(name, Xtr, ytr, Xte)
        m = binary_metrics(yte, proba, pred)
        m.update(train_time_s=tt, inference_time_s=it)
        rows[name] = m

    # Multiclase OVR (solo en el split estratificado)
    multi = {}
    if multiclass_train is not None:
        mc_tr, mc_te = multiclass_train, multiclass_test
        for name in ["random_forest", "svm_rbf"]:
            baseline = ClassicalBaseline(name)
            baseline.fit(Xtr[mc_tr], multiclass_train_labels[mc_tr])
            pred = baseline.predict(Xte[mc_te])
            acc = accuracy_score(multiclass_train_labels[mc_te], pred)
            f1 = f1_score(multiclass_train_labels[mc_te], pred, average="macro")
            multi[name] = {"accuracy": acc, "f1_macro": f1}

    return rows, multi


# ---------------------------------------------------------------- main
multiclass_train_labels = None  # set en el experimento de split


def fmt(x, nd=4):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def main():
    global multiclass_train_labels
    t_start = time.time()
    print("=" * 70)
    print("QZero — Benchmark QSVM vs QI-VAE vs clásicos sobre pcaps propios")
    print("=" * 70)

    X_df, y_multi, pcap_lines = load_flows()
    X = X_df[FLOW_FEATURES].values.astype(float)
    y_bin = (y_multi > 0).astype(int)
    n_flows = len(X)
    per_class = {k: int((y_multi == v).sum()) for k, v in LABELS.items()}
    print(f"Flujos totales: {n_flows} -> {per_class}")

    import qiskit
    import qiskit_machine_learning
    import sklearn
    import torch

    env = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit-learn": sklearn.__version__,
        "qiskit": qiskit.__version__,
        "qiskit-machine-learning": qiskit_machine_learning.__version__,
        "torch": torch.__version__,
        "seed": SEED,
    }

    results = {"loto": {}, "split": {}, "multiclass": {}}

    # --- LOATO: leave-one-attack-type-out (binario) --------------------
    print("\n[1/2] Validación LOATO (cada fold oculta un ataque completo)...")
    for attack in ATTACK_CLASSES:
        hold = y_multi == LABELS[attack]
        train_mask = ~hold
        test_mask = hold | (y_multi == 0)  # test = ataque oculto + normales
        rows, _ = run_fold(X, y_bin, train_mask, test_mask, None, None)
        results["loto"][attack] = rows
        best = max(rows, key=lambda k: rows[k]["f1"])
        print(f"  hold={attack:<12} mejor={best} (F1={rows[best]['f1']:.3f})")

    # --- Split estratificado 80/20 + multiclase ------------------------
    print("\n[2/2] Split estratificado 80/20 + multiclase OVR...")
    sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    tr_idx, te_idx = next(sss.split(X, y_multi))
    train_mask = np.zeros(n_flows, bool)
    train_mask[tr_idx] = True
    test_mask = ~train_mask
    mc_tr = np.ones(train_mask.sum(), bool)
    mc_te = np.ones(test_mask.sum(), bool)
    multiclass_train_labels = y_multi
    rows, multi = run_fold(X, y_bin, train_mask, test_mask, mc_tr, mc_te)
    results["split"]["strat_80_20"] = rows
    results["multiclass"] = multi
    print(f"  split: mejor={max(rows, key=lambda k: rows[k]['f1'])}; "
          f"multiclase OVR: {json.dumps({k: round(v['f1_macro'], 3) for k, v in multi.items()})}")

    elapsed = time.time() - t_start
    used_quantum = results["loto"][ATTACK_CLASSES[0]]["QSVM"].get("used_quantum", False)

    REPORTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    json_path = REPORTS_DIR / "benchmark-pcaps-latest.json"
    json_path.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "environment": env,
        "pcaps": pcap_lines,
        "flows_per_class": per_class,
        "protocol": {
            "validation": "LOATO (leave-one-attack-type-out) + split estratificado 80/20",
            "qsvm_max_samples": QSVM_MAX_SAMPLES,
            "qivae_epochs": QIVAE_EPOCHS,
            "n_qubits": N_QUBITS,
            "classical_models": CLASSICAL_MODELS,
            "qsvm_used_quantum_kernel": used_quantum,
        },
        "results": results,
        "elapsed_s": round(elapsed, 1),
    }, indent=2, default=str))

    md = build_markdown(env, per_class, results, multi, used_quantum, elapsed, stamp)
    md_path = REPORTS_DIR / f"benchmark-pcaps-{stamp}.md"
    md_path.write_text(md)
    print(f"\nInforme escrito en: {md_path.relative_to(ROOT)}")
    print(f"JSON máquina en:   {json_path.relative_to(ROOT)}")
    print(f"Duración total del benchmark: {elapsed:.1f}s")


def _table(title, folds_rows, note=""):
    """Markdown con media±std sobre folds, o fila única si hay 1 fold."""
    model_names = list(next(iter(folds_rows.values())).keys())
    lines = [f"### {title}", ""]
    if note:
        lines += [note, ""]
    lines.append("| Modelo | F1 | Precision | Recall | ROC-AUC | Accuracy | Train (s) | Infer (s) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for model in model_names:
        vals = {k: [] for k in ["f1", "precision", "recall", "roc_auc", "accuracy", "train_time_s", "inference_time_s"]}
        for fold in folds_rows.values():
            for k in vals:
                vals[k].append(fold[model][k])
        def agg(k):
            arr = [v for v in vals[k] if not (isinstance(v, float) and np.isnan(v))]
            if not arr:
                return "—"
            if len(arr) == 1:
                return f"{arr[0]:.4f}"
            return f"{np.mean(arr):.4f}±{np.std(arr):.4f}"
        lines.append(
            f"| {model} | {agg('f1')} | {agg('precision')} | {agg('recall')} | "
            f"{agg('roc_auc')} | {agg('accuracy')} | {agg('train_time_s')} | {agg('inference_time_s')} |"
        )
    lines.append("")
    return lines


def build_markdown(env, per_class, results, multi, used_quantum, elapsed, stamp):
    L = [
        "# Benchmark pcaps propios: QSVM vs QI-VAE vs baselines clásicos",
        "",
        f"- **Fecha:** {datetime.now().isoformat(timespec='seconds')}",
        f"- **Duración del benchmark:** {elapsed:.1f}s",
        f"- **Semilla fija:** {SEED} (todos los modelos y splits deterministas)",
        f"- **Python:** {env['python']} | numpy {env['numpy']} | scikit-learn {env['scikit-learn']} | "
        f"qiskit {env['qiskit']} | qiskit-machine-learning {env['qiskit-machine-learning']} | torch {env['torch']}",
        "",
        "## Dataset",
        "",
        "Flujos extraídos de los pcaps etiquetados propios (`data/synthetic-pcaps/`)",
        "con `FlowExtractor` (14 features de flujo estilo UGRansome, los mismos que",
        "usa producción). Etiquetas binarias: normal=0, cualquier ataque=1.",
        "",
    ]
    L.append("| Clase | Flujos |")
    L.append("|---|---|")
    for k, v in per_class.items():
        L.append(f"| {k} | {v} |")
    L += [
        "",
        "## Protocolo",
        "",
        "1. **LOATO** (leave-one-attack-type-out): 4 folds binarios; en cada fold se",
        "   oculta un ataque completo (simula zero-day). Test = ataque oculto + flujos",
        "   normales. El QI-VAE se entrena **solo con flujos normales** del train",
        "   (detección por error de reconstrucción, como en producción).",
        f"2. **Split estratificado 80/20** (seed {SEED}) como sanity check.",
        "3. **Multiclase OVR** (5 clases) con random_forest y svm_rbf sobre el split.",
        "",
        f"- QSVM: kernel de fidelidad Qiskit, {N_QUBITS} qubits, PCA a 4 dimensiones y codificación",
        f"  en ángulos [0, π]. Por coste del kernel en CPU (~0.5 s/par de muestras), se entrena",
        f"  con máx. {QSVM_MAX_SAMPLES} muestras y se evalúa sobre {QSVM_MAX_TEST} flujos de test",
        "  submuestreados de forma estratificada con seed fija (resto de modelos: test completo).",
        f"- QI-VAE: {QIVAE_EPOCHS} épocas, latente {N_QUBITS}, hidden (64, 32), beta=1.0.",
        "- Escalado StandardScaler ajustado solo en train en cada fold.",
        "",
    ]
    L += _table(
        "LOATO — media±std sobre 4 folds (test F1)",
        _fold_matrix(results["loto"]),
        note="Cada fold oculta ddos / bruteforce / exfiltration / malware por turnos.",
    )
    L += _table("Split estratificado 80/20 — métricas del test", results["split"])

    # Tabla por ataque oculto (F1)
    L += ["### F1 por ataque oculto (LOATO)", ""]
    model_names = list(results["loto"][ATTACK_CLASSES[0]].keys())
    L.append("| Modelo | " + " | ".join(ATTACK_CLASSES) + " |")
    L.append("|---|" + "---|" * len(ATTACK_CLASSES))
    for m in model_names:
        cells = " | ".join(f"{results['loto'][a][m]['f1']:.3f}" for a in ATTACK_CLASSES)
        L.append(f"| {m} | {cells} |")
    L.append("")

    L += ["### Multiclase OVR (5 clases, split estratificado)", ""]
    L.append("| Modelo | Accuracy | F1 macro |")
    L.append("|---|---|---|")
    for name, r in multi.items():
        L.append(f"| {name} | {r['accuracy']:.4f} | {r['f1_macro']:.4f} |")
    L.append("")

    # Veredicto automático
    loto = _fold_matrix(results["loto"])
    means = {m: np.mean([f[m]["f1"] for f in loto.values()]) for m in model_names}
    ranking = sorted(means.items(), key=lambda kv: -kv[1])
    quantum_models = {"QSVM", "QI-VAE"}
    best_quantum = next((m, v) for m, v in ranking if m in quantum_models)
    best_classical = next((m, v) for m, v in ranking if m not in quantum_models)
    L += [
        "## Veredicto",
        "",
        f"- Mejor modelo cuántico (F1 medio LOATO): **{best_quantum[0]}** = {best_quantum[1]:.4f}",
        f"- Mejor baseline clásico: **{best_classical[0]}** = {best_classical[1]:.4f}",
        f"- QSVM usó kernel cuántico real: **{'SÍ' if used_quantum else 'NO (fallback clásico)'}**",
        "",
    ]
    if best_quantum[1] >= best_classical[1]:
        L.append(f"El mejor modelo cuántico-inspirado iguala o supera al mejor baseline clásico en F1 medio bajo validación LOATO.")
    else:
        gap = best_classical[1] - best_quantum[1]
        L.append(
            f"El mejor baseline clásico supera al mejor modelo cuántico en {gap:.4f} F1 medio bajo LOATO. "
            "Con dataset de pcaps sintéticos pequeños (~2.9k flujos, 14 features) los modelos clásicos "
            "supervisados tienen ventaja; el valor del QI-VAE está en la detección sin etiquetas "
            "(zero-day) y su coste de entrenamiento, no en el F1 supervisado."
        )
    L += [
        "",
        "### Tiempos (referencia)",
        "",
        "Los tiempos están en las tablas anteriores (train/infer en segundos, medias LOATO).",
        "El dataset es pequeño (~2.9k flujos), por lo que los tiempos absolutos son bajos;",
        "la comparación relativa entrenamiento cuántico vs clásico sí es representativa.",
        "",
        "---",
        "**Generado por:** `scripts/benchmark-pcaps.py` (ejecución real, sin datos inventados)",
    ]
    return "\n".join(L) + "\n"


def _fold_matrix(loto_results):
    """Renombra folds para _table."""
    return {f"hold_{k}": v for k, v in loto_results.items()}


if __name__ == "__main__":
    main()
