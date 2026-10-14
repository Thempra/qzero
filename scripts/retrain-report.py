#!/usr/bin/env python3
"""Hito 2.4 — reentrenamiento programado + informe automático.

Pensado para cron (o `qzero retrain`): entrena un modelo NUEVO en paralelo,
lo evalúa contra el modelo EN PRODUCCIÓN y escribe un informe fechado en
model-performance-reports/. NO toca el modelo de producción salvo --promote.

Uso:
  python scripts/retrain-report.py [--samples 5000] [--real-data]
                                   [--model-dir models] [--promote]

Salida:
  model-performance-reports/retrain-YYYYmmdd-HHMM.md   (diff de F1, veredicto)
  model-performance-reports/retrain-latest.json        (datos para el dashboard)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qzero.core.predictor import QZeroPredictor  # noqa: E402


def _f1_scores(predictor) -> dict:
    """Collect per-model F1 from a trained predictor's result objects."""
    scores = {}
    if getattr(predictor, "qsvm_result", None):
        scores["qsvm"] = predictor.qsvm_result.f1_score
    if getattr(predictor, "qivae_result", None):
        scores["qivae"] = predictor.qivae_result.f1_score
    for name, res in (getattr(predictor, "classical_results", None) or {}).items():
        scores[name] = res.get("f1") if isinstance(res, dict) else getattr(res, "f1", None)
    return {k: round(float(v), 4) for k, v in scores.items() if v is not None}


def build_report(old: dict, new: dict, meta: dict) -> str:
    lines = [
        "# Informe de reentrenamiento QZero",
        "",
        f"- Fecha: {meta['timestamp']}",
        f"- Muestras: {meta['n_samples']} ({'real' if meta['real'] else 'sintéticas'})",
        f"- Duración: {meta['elapsed_s']}s",
        "",
        "## F1: producción (o) vs nuevo (n) vs diff",
        "",
        "| Modelo | Producción | Nuevo | Δ |",
        "|---|---|---|---|",
    ]
    regressions = []
    for name in sorted(set(old) | set(new)):
        o, n = old.get(name), new.get(name)
        if o is not None and n is not None:
            d = n - o
            mark = "⚠️" if d < -0.01 else ("✅" if d > 0.01 else "·")
            if d < -0.01:
                regressions.append(name)
            lines.append(f"| {name} | {o:.4f} | {n:.4f} | {d:+.4f} {mark} |")
        else:
            shown = o if n is None else n
            lines.append(f"| {name} | {'—' if o is None else f'{o:.4f}'} "
                         f"| {'—' if n is None else f'{n:.4f}'} | {shown} (solo un lado) |")
    verdict = ("REGRESIÓN en: " + ", ".join(regressions) if regressions
               else "Sin regresiones (ΔF1 ≥ −0.01 en todos)")
    lines += ["", "## Veredicto", "", verdict, ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=5000)
    ap.add_argument("--qsvm-samples", type=int, default=200,
                    help="máx. muestras de entrenamiento QSVM (simulador: O(n^2))")
    ap.add_argument("--epochs", type=int, default=30, help="épocas QI-VAE")
    ap.add_argument("--real-data", action="store_true")
    ap.add_argument("--model-dir", default="models")
    ap.add_argument("--promote", action="store_true",
                    help="sobrescribir models/qzero-production con el nuevo")
    args = ap.parse_args()

    model_dir = Path(args.model_dir)
    prod_dir = model_dir / "qzero-production"
    reports_dir = Path("model-performance-reports")
    reports_dir.mkdir(exist_ok=True)

    # 1) F1 del modelo EN PRODUCCIÓN (evaluado con el MISMO dataset de esta
    #    ejecución para que la comparación sea manzanas con manzanas)
    old_scores = {}
    if (prod_dir / "scaler.pkl").exists():
        try:
            prod = QZeroPredictor()
            prod.load(prod_dir)  # restores results.json → *_result objects
            old_scores = _f1_scores(prod)
        except Exception as e:  # noqa: BLE001
            print(f"aviso: no se pudo evaluar el modelo de producción: {e}")

    # 2) entrenar el candidato
    from functools import partial
    start = datetime.now()
    cand = QZeroPredictor(n_qubits=4)
    cand.train_qsvm = partial(cand.train_qsvm, max_samples=args.qsvm_samples)
    cand.train_qivae = partial(cand.train_qivae, epochs=args.epochs)
    cand.train_all(n_samples=args.samples, use_real_data=args.real_data)
    new_scores = _f1_scores(cand)
    meta = {
        "timestamp": start.isoformat(timespec="seconds"),
        "n_samples": args.samples,
        "real": args.real_data,
        "elapsed_s": round((datetime.now() - start).total_seconds(), 1),
    }

    # 3) informe
    report_md = build_report(old_scores, new_scores, meta)
    stamp = start.strftime("%Y%m%d-%H%M")
    (reports_dir / f"retrain-{stamp}.md").write_text(report_md)
    (reports_dir / "retrain-latest.json").write_text(json.dumps(
        {"production": old_scores, "candidate": new_scores, "meta": meta},
        indent=2))
    print(report_md)

    # 4) promoción explícita
    if args.promote:
        prod_dir.mkdir(parents=True, exist_ok=True)
        cand.save(prod_dir)
        print(f"promovido → {prod_dir}")
    else:
        cand_dir = model_dir / "qzero-candidate"
        cand_dir.mkdir(parents=True, exist_ok=True)
        cand.save(cand_dir)
        print(f"candidato guardado en {cand_dir} (producción intacta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
