#!/usr/bin/env python3
"""
Benchmark de DETECCIÓN honesto de QZero — Fase 1.6.

No publica un F1 suelto. Publica el banco, sus defectos y la matriz de
confusión completa, junto con un baseline trivial (predecir siempre la clase
mayoritaria). Si el banco es degenerado, el script lo dice en su propia salida
y en su propio veredicto: no hay forma de leer los números sin leer el aviso.

Qué calcula
-----------
(a) flujos y filas únicas en el banco (todas las features, redondeadas)
(b) features con varianza cero (tol 1e-12) y cuáles son
(c) porcentaje de flujos con <=1 paquete en dirección forward
(d) matriz de confusión 2x2 completa (TN/FP/FN/TP) + accuracy/precision/recall/
    F1/ROC-AUC, para el modelo Y para el baseline mayoritario
(e) baseline trivial: predecir siempre la clase mayoritaria
(f) chequeo de fuga de etiqueta: qué accuracy alcanza el mejor clasificador de
    UN SOLO feature (stump con umbral óptimo). Si un feature suelto iguala al
    modelo, el banco está resuelto por construcción y el F1 no mide detección.

Modelo
------
Se carga models/qivae.pkl si existe. No existe en el repo (el artefacto no está
publicado ni versionado), así que por defecto se entrena un QI-VAE aquí mismo
con la misma arquitectura y semilla que scripts/benchmark-pcaps.py y se declara
en model.source. Entrenar en el banco y medir en el banco es lo que ya hacía el
benchmark viejo; aquí se hace un split estratificado 80/20 y el modelo se
entrena SOLO con normales del train.

Uso
---
    .venv/bin/python scripts/bench_detection.py
    .venv/bin/python scripts/bench_detection.py --pcap-dir data/synthetic-pcaps
    .venv/bin/python scripts/bench_detection.py --seed 7 --test-size 0.3

Salida: model-performance-reports/bench-detection-<timestamp>.json (crudo) y un
resumen por stdout que incluye el veredicto sobre el banco.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

logging.getLogger("qzero").setLevel(logging.ERROR)

REPORTS_DIR = ROOT / "model-performance-reports"
DEFAULT_MODEL = ROOT / "models" / "qivae.pkl"
PCAP_DIR = ROOT / "data" / "synthetic-pcaps"

LABELS = {"normal": 0, "ddos": 1, "bruteforce": 2, "exfiltration": 3, "malware": 4}
ATTACK_CLASSES = ["ddos", "bruteforce", "exfiltration", "malware"]

# Umbrales con los que se declara un banco degenerado. No son arbitrarios: son
# las condiciones bajo las que un F1 no puede distinguir dos clasificadores.
DEGENERATE_RULES = {
    "min_unique_rows_pct": 5.0,      # <5% de filas únicas => banco colapsado
    "max_zero_var_features": 2,      # >2 features constantes de 14
    "max_single_packet_share_pct": 50.0,  # >50% de flujos de un solo paquete
    "max_stump_accuracy_gap": 0.05,  # un feature suelto a <5pts del modelo => fuga
}


# --------------------------------------------------------------------------
# Funciones puras — testeadas en tests/test_fase1_bench.py
# --------------------------------------------------------------------------
def confusion_matrix(
    y_true: Sequence[int], y_pred: Sequence[int]
) -> Dict[str, int]:
    """Matriz de confusión binaria completa. Positivo = 1 = anomalía.

    Devuelve tn/fp/fn/tp y los totales. No colapsa nada a un solo número.

    La etiqueta se binariza con ``!= 0``: una etiqueta multiclase (2=dDoS,
    3=exfiltración…) cuenta como anomalía. Sin esto, un 2 no caía en ninguna de
    las cuatro celdas y los totales no sumaban n — un error silencioso que
    hinchaba la accuracy.
    """
    yt = (np.asarray(y_true).astype(int).ravel() != 0).astype(int)
    yp = (np.asarray(y_pred).astype(int).ravel() != 0).astype(int)
    if yt.size != yp.size:
        raise ValueError(f"tamaños distintos: y_true={yt.size} y_pred={yp.size}")
    tn = int(np.sum((yt == 0) & (yp == 0)))
    fp = int(np.sum((yt == 0) & (yp == 1)))
    fn = int(np.sum((yt == 1) & (yp == 0)))
    tp = int(np.sum((yt == 1) & (yp == 1)))
    return {"tn": tn, "fp": fp, "fn": fn, "tp": tp, "n": int(yt.size)}


def metrics_from_cm(cm: Dict[str, int]) -> Dict[str, float]:
    """Deriva accuracy/precision/recall/F1/FPR de la matriz de confusión."""
    tn, fp, fn, tp = cm["tn"], cm["fp"], cm["fn"], cm["tp"]
    n = tn + fp + fn + tp

    def _div(a: float, b: float) -> float:
        return float(a) / float(b) if b else 0.0

    precision = _div(tp, tp + fp)
    recall = _div(tp, tp + fn)
    f1 = _div(2 * precision * recall, precision + recall)
    return {
        "accuracy": _div(tp + tn, n),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": _div(fp, fp + tn),
        "specificity": _div(tn, tn + fp),
        "npv": _div(tn, tn + fn),
        "balanced_accuracy": 0.5 * (recall + _div(tn, tn + fp)),
    }


def zero_variance_features(
    df: pd.DataFrame, tol: float = 1e-12
) -> List[str]:
    """Features numéricas cuya varianza es <= tol (constantes en el banco)."""
    out: List[str] = []
    for col in df.columns:
        series = pd.to_numeric(df[col], errors="coerce")
        if series.isna().all():
            out.append(str(col))
            continue
        vals = series.dropna().to_numpy(dtype=float)
        if vals.size == 0 or float(np.var(vals)) <= tol:
            out.append(str(col))
    return out


def unique_row_count(df: pd.DataFrame, decimals: int = 6) -> int:
    """Filas únicas tras redondear, para que el ruido float no invente variedad."""
    return int(len(df.round(decimals).drop_duplicates()))


def single_packet_share(df: pd.DataFrame) -> Dict[str, Any]:
    """Fracción de flujos con <=1 paquete forward (sin conversación real)."""
    if "total_fwd_packets" not in df.columns:
        raise ValueError("falta la columna total_fwd_packets")
    fwd = pd.to_numeric(df["total_fwd_packets"], errors="coerce").fillna(0).to_numpy()
    n = int(fwd.size)
    single = int(np.sum(fwd <= 1))
    return {
        "n_flows": n,
        "single_fwd_packet": single,
        "single_fwd_packet_pct": round(100.0 * single / n, 2) if n else 0.0,
        "median_fwd_packets": float(np.median(fwd)) if n else 0.0,
        "max_fwd_packets": float(np.max(fwd)) if n else 0.0,
    }


def majority_baseline(y_true: Sequence[int]) -> Dict[str, Any]:
    """Baseline trivial: predecir siempre la clase mayoritaria del train."""
    yt = np.asarray(y_true).astype(int).ravel()
    if yt.size == 0:
        raise ValueError("y_true vacío")
    values, counts = np.unique(yt, return_counts=True)
    majority = int(values[int(np.argmax(counts))])
    pred = np.full(yt.shape, majority, dtype=int)
    cm = confusion_matrix(yt, pred)
    return {
        "majority_class": majority,
        "prediction_rule": f"siempre {majority}",
        **cm,
        **metrics_from_cm(cm),
    }


def best_single_feature_stump(
    X: pd.DataFrame, y: Sequence[int]
) -> Dict[str, Any]:
    """Mejor stump (1 feature + 1 umbral) sobre accuracy. Mide fuga de etiqueta.

    Prueba umbrales en los valores observados (mediana de puntos de corte) y las
    dos orientaciones. Si esto acierta tanto como el modelo, el banco está
    resuelto por una sola columna.
    """
    yt = np.asarray(y).astype(int).ravel()
    best: Dict[str, Any] = {"feature": None, "threshold": None, "accuracy": 0.0,
                            "direction": None}
    for col in X.columns:
        vals = pd.to_numeric(X[col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        uniq = np.unique(vals)
        if uniq.size < 2:
            continue
        # puntos de corte: entre valores consecutivos, submuestreados a 200
        cuts = (uniq[:-1] + uniq[1:]) / 2.0
        if cuts.size > 200:
            idx = np.linspace(0, cuts.size - 1, 200).astype(int)
            cuts = cuts[idx]
        for thr in cuts:
            above = (vals > thr).astype(int)
            for direction, pred in ((">", above), ("<=", 1 - above)):
                acc = float(np.mean(pred == yt))
                if acc > best["accuracy"]:
                    best = {
                        "feature": str(col),
                        "threshold": float(thr),
                        "accuracy": acc,
                        "direction": direction,
                    }
    return best


def verdict(bank_stats: Dict[str, Any], model_f1: float, baseline_f1: float,
            stump_acc: float, model_acc: float) -> Dict[str, Any]:
    """Decide si el banco permite comparar clasificadores. Reglas explícitas."""
    reasons: List[str] = []
    if bank_stats["unique_rows_pct"] < DEGENERATE_RULES["min_unique_rows_pct"]:
        reasons.append(
            f"solo {bank_stats['unique_rows']} filas únicas ({bank_stats['unique_rows_pct']}%) "
            f"de {bank_stats['n_flows']} flujos"
        )
    if bank_stats["n_zero_variance"] > DEGENERATE_RULES["max_zero_var_features"]:
        reasons.append(
            f"{bank_stats['n_zero_variance']} de {bank_stats['n_features']} features "
            f"con varianza cero"
        )
    if bank_stats["single_packet_pct"] > DEGENERATE_RULES["max_single_packet_share_pct"]:
        reasons.append(
            f"{bank_stats['single_packet_pct']}% de flujos con <=1 paquete forward"
        )
    if model_f1 > 0 and abs(model_f1 - baseline_f1) < 0.01:
        reasons.append(
            f"el modelo empata con el baseline trivial (F1 {model_f1:.4f} vs "
            f"{baseline_f1:.4f})"
        )
    if stump_acc and (model_acc - stump_acc) < DEGENERATE_RULES["max_stump_accuracy_gap"]:
        reasons.append(
            f"un solo feature alcanza accuracy {stump_acc:.4f} frente a {model_acc:.4f} "
            f"del modelo (fuga de etiqueta)"
        )
    degenerate = len(reasons) >= 2
    return {
        "degenerate": degenerate,
        "reasons": reasons,
        "statement": (
            "BANCO DEGENERADO: los números de detección de este JSON NO permiten "
            "afirmar capacidad de detección ni comparar clasificadores. " + " | ".join(reasons)
            if degenerate else
            "El banco no cumple los criterios de degeneración de DEGENERATE_RULES; "
            "aun así, es tráfico sintético y no sustituye a un corpus real."
        ),
        "rules": DEGENERATE_RULES,
    }


# --------------------------------------------------------------------------
# Carga del banco
# --------------------------------------------------------------------------
def load_bank(pcap_dir: Path) -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
    """Extrae flujos etiquetados de los pcaps, igual que benchmark-pcaps.py."""
    from scapy.all import rdpcap

    from qzero.preprocessing.flow_extractor import FlowExtractor

    if not pcap_dir.is_dir():
        raise FileNotFoundError(f"no existe el directorio de pcaps: {pcap_dir}")
    extractor = FlowExtractor()
    frames, labels, lines = [], [], []
    for pcap in sorted(pcap_dir.glob("*.pcap")):
        label = next((k for k in LABELS if pcap.name.startswith(k)), None)
        if label is None:
            continue
        pkts = list(rdpcap(str(pcap)))
        df = extractor.extract_flows_from_packets(pkts)
        frames.append(df)
        labels.append(np.full(len(df), LABELS[label]))
        lines.append(f"{pcap.name} ({label}): {len(pkts)} paquetes -> {len(df)} flujos")
    if not frames:
        raise FileNotFoundError(f"no hay pcaps etiquetados en {pcap_dir}")
    return pd.concat(frames, ignore_index=True), np.concatenate(labels), lines


def bank_stats(df: pd.DataFrame, y: np.ndarray) -> Dict[str, Any]:
    zv = zero_variance_features(df)
    sp = single_packet_share(df)
    uniq = unique_row_count(df)
    return {
        "n_flows": int(len(df)),
        "n_features": int(df.shape[1]),
        "features": [str(c) for c in df.columns],
        "unique_rows": uniq,
        "unique_rows_pct": round(100.0 * uniq / len(df), 2) if len(df) else 0.0,
        "zero_variance_features": zv,
        "n_zero_variance": len(zv),
        "single_packet_pct": sp["single_fwd_packet_pct"],
        "single_packet_detail": sp,
        "distinct_flow_duration": int(df["flow_duration"].nunique())
        if "flow_duration" in df.columns else None,
        "class_counts": {str(k): int(v) for k, v in zip(*np.unique(y, return_counts=True))},
    }


# --------------------------------------------------------------------------
# Modelo
# --------------------------------------------------------------------------
def fit_qivae(X_normal: np.ndarray, epochs: int, seed: int):
    from qzero.quantum.qivae import QIVAE, QIVAEConfig

    cfg = QIVAEConfig(
        input_dim=X_normal.shape[1],
        latent_dim=4,
        hidden_dims=(64, 32),
        epochs=epochs,
        batch_size=32,
        beta=1.0,
        random_state=seed,
    )
    model = QIVAE(cfg)
    model.fit(X_normal, verbose=False)
    return model


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Benchmark de detección honesto de QZero")
    ap.add_argument("--pcap-dir", type=Path, default=PCAP_DIR)
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    ap.add_argument("--test-size", type=float, default=0.2)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    print(f"[det] banco: {args.pcap_dir}")
    X_df, y_multi, lines = load_bank(args.pcap_dir)
    for line in lines:
        print(f"[det]   {line}")

    stats = bank_stats(X_df, y_multi)
    print(f"[det] flujos={stats['n_flows']}  filas únicas={stats['unique_rows']} "
          f"({stats['unique_rows_pct']}%)  features={stats['n_features']}")
    print(f"[det] features con varianza cero ({stats['n_zero_variance']}): "
          f"{', '.join(stats['zero_variance_features']) or 'ninguna'}")
    print(f"[det] flujos con <=1 paquete forward: {stats['single_packet_pct']}%")

    y_bin = (y_multi != 0).astype(int)

    # Split estratificado 80/20 por clase multi-clase, para que el test tenga
    # todas las clases de ataque. El modelo se entrena SOLO con normales del train.
    idx_tr, idx_te = train_test_split(
        np.arange(len(y_multi)),
        test_size=args.test_size,
        random_state=args.seed,
        stratify=y_multi,
    )
    X = X_df.to_numpy(dtype=float)
    scaler = StandardScaler().fit(X[idx_tr])

    if args.model.exists():
        import pickle

        with open(args.model, "rb") as fh:
            qivae = pickle.load(fh)
        model_meta = {"source": f"loaded:{args.model}"}
        print(f"[det] modelo cargado de {args.model}")
    else:
        model_meta = {
            "source": "trained-in-bench",
            "why": "models/qivae.pkl no existe en el repo (no está versionado); se "
                   "entrena un QI-VAE con la arquitectura de scripts/benchmark-pcaps.py",
            "epochs": args.epochs,
            "trained_on": "solo normales del split de train",
            "seed": args.seed,
        }
        normal_tr = X[idx_tr][y_bin[idx_tr] == 0]
        qivae = fit_qivae(scaler.transform(normal_tr), args.epochs, args.seed)
        print(f"[det] modelo entrenado aquí sobre {len(normal_tr)} normales "
              f"({args.epochs} epochs)")

    Xte = scaler.transform(X[idx_te])
    yte = y_bin[idx_te]
    yte_multi = y_multi[idx_te]

    if hasattr(qivae, "reconstruction_errors"):
        scores = np.asarray(qivae.reconstruction_errors(Xte), dtype=float)
        pred = np.asarray(qivae.predict(Xte), dtype=int)
    else:  # predictor serializado
        scores = np.asarray(qivae.get_anomaly_score(Xte), dtype=float)
        pred = (scores > 0.5).astype(int)

    cm = confusion_matrix(yte, pred)
    model_metrics = metrics_from_cm(cm)
    try:
        model_metrics["roc_auc"] = float(roc_auc_score(yte, scores))
    except ValueError:
        model_metrics["roc_auc"] = float("nan")

    base = majority_baseline(yte)
    stump = best_single_feature_stump(X_df.iloc[idx_tr], y_bin[idx_tr])
    ver = verdict(stats, model_metrics["f1"], base["f1"],
                  stump["accuracy"], model_metrics["accuracy"])

    # recall por clase de ataque en el test
    per_class: Dict[str, Any] = {}
    for name, code in LABELS.items():
        mask = yte_multi == code
        if mask.sum() == 0:
            per_class[name] = {"n": 0, "detected": 0, "recall": None}
            continue
        detected = int(pred[mask].sum())
        per_class[name] = {
            "n": int(mask.sum()),
            "detected": detected,
            "recall": round(detected / int(mask.sum()), 4),
        }

    print("\n[det] MATRIZ DE CONFUSIÓN — modelo (test n=%d)" % cm["n"])
    print(f"[det]   TN={cm['tn']}  FP={cm['fp']}  FN={cm['fn']}  TP={cm['tp']}")
    print(f"[det]   accuracy={model_metrics['accuracy']:.4f} "
          f"precision={model_metrics['precision']:.4f} "
          f"recall={model_metrics['recall']:.4f} F1={model_metrics['f1']:.4f} "
          f"FPR={model_metrics['fpr']:.4f} ROC-AUC={model_metrics['roc_auc']:.4f}")
    print(f"[det] BASELINE trivial (siempre clase {base['majority_class']}): "
          f"accuracy={base['accuracy']:.4f} F1={base['f1']:.4f}")
    print(f"[det] Mejor stump de 1 feature: {stump['feature']} {stump['direction']} "
          f"{stump['threshold']} -> accuracy={stump['accuracy']:.4f}")
    print(f"[det] recall por clase: "
          + ", ".join(f"{k}={v['recall']}" for k, v in per_class.items()))
    print(f"\n[det] VEREDICTO: {'DEGENERADO' if ver['degenerate'] else 'no degenerado'}")
    for r in ver["reasons"]:
        print(f"[det]   - {r}")
    print(f"[det] {ver['statement']}")

    stamp = datetime.now(timezone.utc).astimezone()
    result = {
        "benchmark": "bench_detection",
        "generated_at": stamp.isoformat(),
        "hardware": {
            "nproc": os.cpu_count(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "config": {
            "pcap_dir": str(args.pcap_dir),
            "test_size": args.test_size,
            "seed": args.seed,
            "model_path": str(args.model),
        },
        "model": model_meta,
        "bank": stats,
        "split": {
            "train": int(len(idx_tr)),
            "test": int(len(idx_te)),
            "stratified_by": "clase multiclase",
        },
        "confusion_matrix": cm,
        "metrics": model_metrics,
        "baseline_majority": base,
        "best_single_feature_stump": stump,
        "per_class_recall": per_class,
        "verdict": ver,
        "caveats": [
            "tráfico 100% sintético generado paquete a paquete: no hay conversación "
            "bidireccional real",
            "la etiqueta está codificada en el tamaño/patrón de paquete del generador "
            "(scripts/generate-synthetic-pcaps-v2.py), así que un stump de 1 feature "
            "puede separar las clases sin detectar nada",
            "QI-VAE entrenado en el propio banco, no en tráfico de producción",
            "no se mide zero-day ni FPR sobre tráfico benigno real: no hay corpus",
        ],
    }

    out = args.out or (REPORTS_DIR / f"bench-detection-{stamp.strftime('%Y-%m-%dT%H-%M-%S')}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False, default=str)
    latest = REPORTS_DIR / "bench-detection-latest.json"
    with open(latest, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False, default=str)
    print(f"\n[det] JSON crudo: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
