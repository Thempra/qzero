#!/usr/bin/env python3
"""
Benchmark de throughput y latencia de QZero — medidas reales, sin maquillar.

Qué mide (y qué NO mide)
------------------------
(a) flujos/s que procesa el pipeline, desglosado en las etapas que de verdad
    existen en producción (detector.analyze lee un pcap con rdpcap y luego
    extrae):
      - I/O pcap: wrpcap/rdpcap sobre un fichero temporal (se borra al acabar)
      - extracción: paquetes -> DataFrame de 14 features (FlowExtractor)
      - inferencia: DataFrame -> scores (QZeroPredictor.get_anomaly_score)
      - extremo a extremo: pcap -> scores
(b) latencia p50/p95/p99 de inferencia POR FLUJO. Se mide flujo a flujo
    (batch de 1) porque es lo que significa "latencia por flujo"; el throughput
    se mide por lotes, que es como se sirve. Ambas cifras se publican por
    separado: mezclarlas es cómo se fabricó el "sub-millisecond" retirado.
(c) CPU % y RSS MB del propio proceso durante la fase de extremo a extremo.

Por qué los paquetes se "disecan" antes de medir
------------------------------------------------
Scapy construye los paquetes de forma perezosa. Un paquete recién creado con
``IP()/TCP()`` no tiene capas diseccionadas: ``FlowExtractor._parse_packet``
llama a ``len(bytes(pkt))``, lo que fuerza la serialización completa de cada
paquete y domina el tiempo (medido: 88.8% del coste del extractor). Eso NO es
lo que ocurre en producción, donde ``rdpcap`` entrega paquetes ya diseccionados.
Por eso el bench hace un round-trip real por un pcap temporal antes de medir, y
publica además la cifra sobre paquetes sin diseccionar en
``extraction_unbuilt_packets`` para que la diferencia quede documentada en vez
de escondida.

Lo que NO entra en la medición, y hay que decirlo:
  - No hay NIC real ni captura en vivo: no se mide Gbps de red ni drops del
    kernel. Ver "excluded_from_measurement"/"no_medido" en el JSON.
  - El modelo: si no se pasa --model y no existe models/qivae.pkl, se entrena
    un QI-VAE aquí mismo con semilla fija. Ese modelo NO es el desplegado (el
    repo no publica qivae.pkl); es un modelo representativo del mismo tamaño y
    arquitectura. El JSON lo declara en model.source.

Uso
---
    .venv/bin/python scripts/bench_throughput.py --flows 2000
    .venv/bin/python scripts/bench_throughput.py --flows 500 --model models/qivae.pkl
    .venv/bin/python scripts/bench_throughput.py --flows 300 --quick   # sin fase por-flujo

Salida: model-performance-reports/bench-throughput-<timestamp>.json (crudo) y un
resumen por stdout. Sin privilegios: no abre sockets, no toca la NIC.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

logging.getLogger("qzero").setLevel(logging.ERROR)

REPORTS_DIR = ROOT / "model-performance-reports"
DEFAULT_MODEL = ROOT / "models" / "qivae.pkl"


# --------------------------------------------------------------------------
# Estadística — funciones puras, testeadas en tests/test_fase1_bench.py
# --------------------------------------------------------------------------
def percentile(values: Sequence[float], q: float) -> float:
    """Percentil con interpolación lineal (mismo criterio que numpy.percentile).

    ``q`` en [0, 100]. Lista vacía -> ValueError (no se inventa un 0).
    """
    if not values:
        raise ValueError("percentile() de una lista vacía")
    if not 0.0 <= q <= 100.0:
        raise ValueError(f"percentil fuera de rango: {q}")
    arr = np.sort(np.asarray(values, dtype=float))
    if arr.size == 1:
        return float(arr[0])
    pos = (q / 100.0) * (arr.size - 1)
    lo = int(np.floor(pos))
    hi = int(np.ceil(pos))
    if lo == hi:
        return float(arr[lo])
    frac = pos - lo
    return float(arr[lo] * (1.0 - frac) + arr[hi] * frac)


def summarize_latencies(samples_ms: Sequence[float]) -> Dict[str, Any]:
    """Resumen de latencias en ms: n, mean, p50, p95, p99, max."""
    if not samples_ms:
        raise ValueError("summarize_latencies() de una lista vacía")
    return {
        "n": int(len(samples_ms)),
        "mean_ms": float(np.mean(samples_ms)),
        "p50_ms": percentile(samples_ms, 50),
        "p95_ms": percentile(samples_ms, 95),
        "p99_ms": percentile(samples_ms, 99),
        "max_ms": float(np.max(samples_ms)),
    }


def rates(n_items: int, elapsed_s: float) -> float:
    """items/segundo. elapsed <= 0 -> 0.0 (nunca infinito)."""
    if elapsed_s <= 0:
        return 0.0
    return float(n_items) / float(elapsed_s)


# --------------------------------------------------------------------------
# Generación de tráfico sintético EN MEMORIA
# --------------------------------------------------------------------------
def build_synthetic_packets(
    n_flows: int,
    seed: int = 42,
    pkt_rate_per_flow: Tuple[int, int] = (2, 12),
) -> List[Any]:
    """Genera conversaciones TCP/UDP/ICMP bidireccionales en memoria.

    A diferencia de scripts/generate-synthetic-pcaps-v2.py (un paquete por
    flujo, sin respuesta), aquí cada flujo es una conversación con paquetes en
    ambos sentidos y tiempos de llegada reales, para que FlowExtractor tenga
    estructura bidireccional que agregar. La etiqueta no existe: esto mide
    coste de cómputo, no detección.
    """
    from scapy.all import ICMP, IP, TCP, UDP

    rng = np.random.default_rng(seed)
    packets: List[Any] = []
    t0 = 1_700_000_000.0  # epoch fijo: reproducibilidad bit a bit del timing

    for i in range(n_flows):
        proto = int(rng.choice([6, 6, 6, 17, 17, 1]))
        client = f"192.168.1.{1 + (i % 250)}"
        server = f"93.184.216.{10 + (i % 40)}"
        sport = int(1024 + (i * 7) % 60000)
        dport = int(rng.choice([80, 443, 22, 53, 8080]))
        n_pkts = int(rng.integers(pkt_rate_per_flow[0], pkt_rate_per_flow[1] + 1))
        # El flujo arranca a lo largo de una ventana de 60 s
        start = t0 + float(rng.uniform(0, 60))
        # ida y vuelta: ~350 µs de RTT local
        ts = start
        for k in range(n_pkts):
            fwd = (k % 2 == 0)
            payload_len = int(rng.choice([0, 64, 512, 1400]))
            payload = b"\x00" * payload_len
            if proto == 6:
                flags = "S" if k == 0 else ("PA" if payload_len else "A")
                if fwd:
                    pkt = IP(src=client, dst=server) / TCP(sport=sport, dport=dport, flags=flags) / payload
                else:
                    pkt = IP(src=server, dst=client) / TCP(sport=dport, dport=sport, flags=flags) / payload
            elif proto == 17:
                if fwd:
                    pkt = IP(src=client, dst=server) / UDP(sport=sport, dport=dport) / payload
                else:
                    pkt = IP(src=server, dst=client) / UDP(sport=dport, dport=sport) / payload
            else:
                if fwd:
                    pkt = IP(src=client, dst=server) / ICMP() / payload
                else:
                    pkt = IP(src=server, dst=client) / ICMP(type=0) / payload
            pkt.time = ts
            packets.append(pkt)
            ts += float(rng.uniform(0.0002, 0.05))
    return packets


# --------------------------------------------------------------------------
# Modelo
# --------------------------------------------------------------------------
def load_or_train_model(
    model_path: Optional[Path],
    n_train: int = 4000,
    epochs: int = 20,
    seed: int = 42,
    cache_path: Optional[Path] = None,
) -> Tuple[Any, Any, Dict[str, Any]]:
    """Carga qivae.pkl si existe; si no, entrena uno aquí y lo declara.

    Si se pasa ``cache_path`` y ya existe, se reutiliza el modelo ya entrenado
    (mismo bench, misma máquina): así las repeticiones miden solo inferencia y
    no vuelven a pagar 60 s de entrenamiento. El JSON declara de dónde salió.

    Devuelve (qivae, scaler, meta).
    """
    import pickle

    from sklearn.preprocessing import StandardScaler

    from qzero.quantum.qivae import QIVAE, QIVAEConfig

    if model_path is not None and Path(model_path).exists():
        with open(model_path, "rb") as fh:
            obj = pickle.load(fh)
        # Acepta tanto un QIVAE suelto como el dict que deja predictor.save()
        if isinstance(obj, dict) and "qivae" in obj:
            obj = obj["qivae"]
        scaler = StandardScaler()
        # Sin scaler publicado no se puede reproducir el preprocesado del modelo
        meta = {
            "source": f"loaded:{model_path}",
            "scaler": "NO DISPONIBLE — se ajusta uno nuevo sobre datos sintéticos "
                      "(las latencias siguen siendo válidas: el scaler es O(features))",
            "epochs": None,
        }
        return obj, scaler, meta

    if cache_path is not None and Path(cache_path).exists():
        with open(cache_path, "rb") as fh:
            blob = pickle.load(fh)
        meta = dict(blob["meta"])
        meta["source"] = f"cache:{cache_path}"
        meta["why"] = ("modelo entrenado por una ejecución previa de este mismo bench "
                       "en esta máquina; el repo no publica models/qivae.pkl")
        return blob["model"], blob["scaler"], meta

    from qzero.preprocessing.data_loader import generate_synthetic_data

    X_df, y = generate_synthetic_data(n_samples=n_train * 2, random_state=seed)
    X = np.asarray(X_df, dtype=float)
    y = np.asarray(y)
    normal = X[y == 0][:n_train]

    scaler = StandardScaler().fit(normal)
    cfg = QIVAEConfig(
        input_dim=X.shape[1],
        latent_dim=4,
        hidden_dims=(64, 32),
        epochs=epochs,
        batch_size=32,
        beta=1.0,
        random_state=seed,
    )
    t0 = time.perf_counter()
    model = QIVAE(cfg)
    model.fit(scaler.transform(normal), verbose=False)
    train_s = time.perf_counter() - t0
    meta = {
        "source": "trained-in-bench",
        "why": "no existe models/qivae.pkl en el repo; se entrena un QI-VAE de la "
               "misma arquitectura que scripts/benchmark-pcaps.py (latent 4, "
               "hidden 64/32) para medir coste de inferencia, no calidad",
        "train_samples": int(normal.shape[0]),
        "epochs": epochs,
        "train_time_s": round(train_s, 3),
        "seed": seed,
    }
    if cache_path is not None:
        try:
            Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "wb") as fh:
                pickle.dump({"model": model, "scaler": scaler, "meta": meta}, fh)
            meta["cached_to"] = str(cache_path)
        except OSError as exc:  # la caché es una comodidad, no un requisito
            meta["cache_error"] = str(exc)
    return model, scaler, meta


def build_predictor(qivae, scaler):
    """QZeroPredictor cableado con el modelo ya ajustado (sin reentrenar)."""
    from qzero.core.predictor import QZeroPredictor

    p = QZeroPredictor(use_qsvm=False, use_classical=False, use_qivae=True)
    p.qivae_model = qivae
    p.scaler = scaler
    p.model_fitted = True
    return p


# --------------------------------------------------------------------------
# Muestreo de CPU / RSS
# --------------------------------------------------------------------------
class ResourceSampler:
    """Hilo que muestrea CPU% y RSS del proceso mientras corre una fase."""

    def __init__(self, interval_s: float = 0.05):
        self.interval_s = interval_s
        self.samples: List[Tuple[float, float]] = []  # (cpu_pct, rss_mb)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._proc = None

    def __enter__(self):
        import psutil

        self._proc = psutil.Process(os.getpid())
        self._proc.cpu_percent(interval=None)  # inicializa el contador
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self):
        while not self._stop.wait(self.interval_s):
            try:
                cpu = self._proc.cpu_percent(interval=None)
                rss = self._proc.memory_info().rss / (1024 * 1024)
                self.samples.append((float(cpu), float(rss)))
            except Exception:  # noqa: BLE001 — el muestreo nunca debe romper la medida
                return

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        return False

    def summary(self, n_cpu: int) -> Dict[str, float]:
        if not self.samples:
            return {"n_samples": 0.0}
        cpu = [s[0] for s in self.samples]
        rss = [s[1] for s in self.samples]
        return {
            "n_samples": float(len(self.samples)),
            "cpu_pct_mean_of_one_core": float(np.mean(cpu)),
            "cpu_pct_peak_of_one_core": float(np.max(cpu)),
            "cpu_pct_of_machine_mean": float(np.mean(cpu) / max(n_cpu, 1)),
            "rss_mb_mean": float(np.mean(rss)),
            "rss_mb_peak": float(np.max(rss)),
        }


# --------------------------------------------------------------------------
# Hardware
# --------------------------------------------------------------------------
def load_average() -> Dict[str, float]:
    """Load average de 1/5/15 min antes y después, para detectar contaminación."""
    try:
        one, five, fifteen = os.getloadavg()
        return {"1m": round(one, 2), "5m": round(five, 2), "15m": round(fifteen, 2)}
    except OSError:
        return {"1m": -1.0, "5m": -1.0, "15m": -1.0}


def hardware_info() -> Dict[str, Any]:
    import torch

    model_name = "desconocido"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                model_name = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    try:
        import psutil

        ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)
    except Exception:  # noqa: BLE001
        ram_gb = None
    return {
        "nproc": os.cpu_count(),
        "cpu_model": model_name,
        "ram_gb": ram_gb,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "torch_num_threads": torch.get_num_threads(),
        "virtualized": "QEMU" in model_name or "KVM" in model_name,
    }


# --------------------------------------------------------------------------
# Fases de medición
# --------------------------------------------------------------------------
def phase_extraction(packets: List[Any]) -> Tuple[Any, Dict[str, Any]]:
    """paquetes -> DataFrame de flujos (una sola pasada)."""
    from qzero.preprocessing.flow_extractor import FlowExtractor

    ex = FlowExtractor()
    t0 = time.perf_counter()
    df = ex.extract_flows_from_packets(packets)
    elapsed = time.perf_counter() - t0
    return df, {
        "packets": len(packets),
        "flows": int(len(df)),
        "elapsed_s": round(elapsed, 4),
        "packets_per_s": round(rates(len(packets), elapsed), 1),
        "flows_per_s": round(rates(len(df), elapsed), 1),
    }


def phase_pcap_roundtrip(packets: List[Any]) -> Tuple[List[Any], Dict[str, Any], Dict[str, Any]]:
    """Escribe y relee un pcap temporal para obtener paquetes DISECADOS.

    Devuelve (packets_disecados, stats_io, stats_extract_unbuilt). El fichero se
    borra siempre, también si falla: no se deja basura en disco.
    """
    import tempfile

    from scapy.all import rdpcap, wrpcap

    from qzero.preprocessing.flow_extractor import FlowExtractor

    tmp = Path(tempfile.mkdtemp(prefix="qz-bench-")) / "bench.pcap"
    try:
        t0 = time.perf_counter()
        wrpcap(str(tmp), packets)
        t_write = time.perf_counter() - t0
        size_mb = tmp.stat().st_size / (1024 * 1024)

        t1 = time.perf_counter()
        dissected = list(rdpcap(str(tmp)))
        t_read = time.perf_counter() - t1
    finally:
        try:
            tmp.unlink(missing_ok=True)
            tmp.parent.rmdir()
        except OSError:
            pass

    io_stats = {
        "pcap_size_mb": round(size_mb, 2),
        "write_s": round(t_write, 4),
        "read_s": round(t_read, 4),
        "packets": len(dissected),
        "read_packets_per_s": round(rates(len(dissected), t_read), 1),
        "note": "rdpcap en un pcap temporal de este bench; el fichero se borra al leerlo",
    }
    # La misma extracción sobre paquetes SIN diseccionar, para documentar el
    # coste de Scapy serializando: no es lo que pasa en producción.
    ex = FlowExtractor()
    t2 = time.perf_counter()
    df_unbuilt = ex.extract_flows_from_packets(packets)
    t_unbuilt = time.perf_counter() - t2
    unbuilt = {
        "packets": len(packets),
        "flows": int(len(df_unbuilt)),
        "elapsed_s": round(t_unbuilt, 4),
        "flows_per_s": round(rates(len(df_unbuilt), t_unbuilt), 1),
        "note": "paquetes construidos en memoria y sin diseccionar: Scapy serializa "
                "cada paquete en len(bytes(pkt)). NO es el camino de producción; "
                "se publica para que la diferencia sea auditable",
    }
    return dissected, io_stats, unbuilt


def phase_inference_latency(
    predictor, X: np.ndarray, max_flows: int
) -> Tuple[List[float], Dict[str, Any]]:
    """Latencia real por flujo: una llamada de scoring por fila, batch=1.

    Es el camino que ejecuta el agente para un flujo suelto: scaler.transform
    + reconstruction_errors + normalize_score (predictor.get_anomaly_score).
    """
    n = min(len(X), max_flows)
    samples_ms: List[float] = []
    # calentamiento: la primera llamada paga inicialización de torch
    predictor.get_anomaly_score(X[:1])
    for i in range(n):
        row = X[i : i + 1]
        t0 = time.perf_counter()
        predictor.get_anomaly_score(row)
        samples_ms.append((time.perf_counter() - t0) * 1000.0)
    return samples_ms, {"flows_timed": n, "batch_size": 1}


def phase_end_to_end(
    packets: List[Any], predictor, batch_size: int = 256, io_stats: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """paquetes(disecados) -> flujos -> scores, con muestreo de CPU/RSS.

    Si se pasa ``io_stats`` del round-trip pcap, la cifra "pcap -> scores"
    incluye también la escritura y lectura del fichero: es el camino real de
    ``detector.analyze()``.
    """
    from qzero.preprocessing.flow_extractor import FlowExtractor

    with ResourceSampler() as sampler:
        t0 = time.perf_counter()
        df = FlowExtractor().extract_flows_from_packets(packets)
        t_extract = time.perf_counter() - t0

        X = np.asarray(df, dtype=float)
        t1 = time.perf_counter()
        chunks = 0
        for i in range(0, len(X), batch_size):
            predictor.get_anomaly_score(X[i : i + batch_size])
            chunks += 1
        t_infer = time.perf_counter() - t1
        total = time.perf_counter() - t0

    io_s = (io_stats["write_s"] + io_stats["read_s"]) if io_stats else 0.0
    total_with_io = total + io_s
    # Camino de producción real: el pcap YA existe, así que solo se lee.
    # La escritura es un artefacto del bench (hay que materializar los paquetes).
    io_read_s = io_stats["read_s"] if io_stats else 0.0
    total_read_io = total + io_read_s

    res = {
        "packets": len(packets),
        "flows": int(len(df)),
        "extract_s": round(t_extract, 4),
        "infer_s": round(t_infer, 4),
        "total_s": round(total, 4),
        "io_pcap_s": round(io_s, 4),
        "io_pcap_read_s": round(io_read_s, 4),
        "total_with_io_s": round(total_with_io, 4),
        "total_read_io_s": round(total_read_io, 4),
        "flows_per_s_end_to_end": round(rates(len(df), total), 1),
        "flows_per_s_end_to_end_with_io": round(rates(len(df), total_with_io), 1),
        "flows_per_s_pcap_to_scores": round(rates(len(df), total_read_io), 1),
        "flows_per_s_infer_only": round(rates(len(df), t_infer), 1),
        "packets_per_s_end_to_end": round(rates(len(packets), total), 1),
        "batch_size": batch_size,
        "batches": chunks,
        "extract_share_pct": round(100.0 * t_extract / total, 2) if total > 0 else 0.0,
    }
    res["resources"] = sampler.summary(os.cpu_count() or 1)
    return res


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Throughput y latencia reales de QZero")
    ap.add_argument("--flows", type=int, default=2000,
                    help="flujos sintéticos a generar (tamaño de muestra)")
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL,
                    help="ruta a qivae.pkl (si no existe, se entrena uno aquí)")
    ap.add_argument("--epochs", type=int, default=20, help="epochs si hay que entrenar")
    ap.add_argument("--latency-flows", type=int, default=500,
                    help="cuántos flujos medir uno a uno (batch=1)")
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="omite la fase por-flujo")
    ap.add_argument("--allow-busy", action="store_true",
                    help="mide aunque el load average 1m supere nproc (resultado dudoso)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--model-cache", type=Path, default=None,
                    help="reutiliza el modelo entrenado por una ejecución anterior "
                         "(evita repagar el entrenamiento en las repeticiones)")
    ap.add_argument("--repeat", type=int, default=1,
                    help="repeticiones de las fases 2-4; publica la mediana")
    args = ap.parse_args(argv)

    load_before = load_average()
    if load_before["1m"] > (os.cpu_count() or 1) * 0.9 and not args.allow_busy:
        print(f"[bench] ABORTADO: load average 1m={load_before['1m']} con "
              f"{os.cpu_count()} cores. Otra carga está contaminando la medida y "
              f"los flujos/s no serían defendibles. Espera a que baje o pasa "
              f"--allow-busy para medir igualmente (quedará marcado en el JSON).")
        return 2
    print(f"[bench] hardware: {hardware_info()}")
    print(f"[bench] load antes: {load_before}")
    print(f"[bench] generando {args.flows} flujos sintéticos en memoria…")
    t_gen = time.perf_counter()
    packets = build_synthetic_packets(args.flows, seed=args.seed)
    gen_s = time.perf_counter() - t_gen
    print(f"[bench] {len(packets)} paquetes generados en {gen_s:.2f} s "
          f"({len(packets) / max(gen_s, 1e-9):.0f} pkt/s de generación, "
          f"FUERA de la medición)")

    print(f"[bench] modelo: {args.model}")
    qivae, scaler, model_meta = load_or_train_model(
        args.model, epochs=args.epochs, seed=args.seed, cache_path=args.model_cache
    )
    predictor = build_predictor(qivae, scaler)
    if "train_time_s" in model_meta:
        print(f"[bench] modelo entrenado en {model_meta['train_time_s']} s "
              f"({model_meta['source']})")

    print("[bench] fase 1/4: round-trip pcap (disección real, fichero temporal)…")
    packets, io_stats, unbuilt = phase_pcap_roundtrip(packets)
    print(f"[bench]   {io_stats['packets']} paquetes, pcap {io_stats['pcap_size_mb']} MB, "
          f"escritura {io_stats['write_s']} s + lectura {io_stats['read_s']} s "
          f"({io_stats['read_packets_per_s']} pkt/s de lectura)")
    print(f"[bench]   (referencia: sobre paquetes SIN diseccionar la extracción da "
          f"{unbuilt['flows_per_s']} flujos/s — artefacto de Scapy, no de producción)")

    runs = []
    all_latency_samples = []
    for rep in range(max(1, args.repeat)):
        if args.repeat > 1:
            print(f"[bench] --- repetición {rep + 1}/{args.repeat} ---")

        print("[bench] fase 2/4: extracción…")
        df, extract = phase_extraction(packets)
        X = np.asarray(df, dtype=float)
        print(f"[bench]   {extract['packets']} paquetes -> {extract['flows']} flujos en "
              f"{extract['elapsed_s']} s = {extract['flows_per_s']} flujos/s "
              f"({extract['packets_per_s']} pkt/s)")

        latency = {"skipped": True}
        if not args.quick:
            print(f"[bench] fase 3/4: latencia por flujo (batch=1, "
                  f"{min(args.latency_flows, len(X))} flujos)…")
            samples, lm = phase_inference_latency(predictor, X, args.latency_flows)
            all_latency_samples.extend(samples)
            stats = summarize_latencies(samples)
            stats.update(lm)
            latency = stats
            print(f"[bench]   p50={stats['p50_ms']:.3f} ms  p95={stats['p95_ms']:.3f} ms  "
                  f"p99={stats['p99_ms']:.3f} ms  max={stats['max_ms']:.3f} ms")

        print("[bench] fase 4/4: extremo a extremo (con muestreo CPU/RSS)…")
        e2e = phase_end_to_end(packets, predictor, batch_size=args.batch_size,
                               io_stats=io_stats)
        print(f"[bench]   {e2e['flows']} flujos en {e2e['total_s']} s = "
              f"{e2e['flows_per_s_end_to_end']} flujos/s "
              f"(extracción {e2e['extract_share_pct']}% del tiempo)")
        print(f"[bench]   con I/O de pcap (lectura+escritura): {e2e['total_with_io_s']} s = "
              f"{e2e['flows_per_s_end_to_end_with_io']} flujos/s")
        print(f"[bench]   pcap ya existente -> scores (solo lectura): "
              f"{e2e['total_read_io_s']} s = {e2e['flows_per_s_pcap_to_scores']} flujos/s")
        print(f"[bench]   CPU {e2e['resources'].get('cpu_pct_mean_of_one_core', 0):.1f}% "
              f"de un core ({e2e['resources'].get('cpu_pct_of_machine_mean', 0):.1f}% "
              f"de la máquina), RSS pico {e2e['resources'].get('rss_mb_peak', 0):.0f} MB")
        runs.append({"extraction": extract, "end_to_end": e2e, "latency": latency})

    extract = runs[0]["extraction"]
    e2e = runs[0]["end_to_end"]
    latency = runs[0]["latency"]

    # Con varias repeticiones se publica la MEDIANA de cada tasa, no la mejor:
    # publicar el mejor caso sería maquillar la cifra.
    summary = {}
    if len(runs) > 1:
        def med(path):
            vals = []
            for r in runs:
                cur = r
                for k in path:
                    cur = cur[k]
                vals.append(float(cur))
            return float(np.median(vals))

        summary = {
            "repeats": len(runs),
            "statistic": "median_of_repeats",
            "flows_per_s_end_to_end": round(med(["end_to_end", "flows_per_s_end_to_end"]), 1),
            "flows_per_s_pcap_to_scores": round(
                med(["end_to_end", "flows_per_s_pcap_to_scores"]), 1),
            "flows_per_s_infer_only": round(med(["end_to_end", "flows_per_s_infer_only"]), 1),
            "flows_per_s_extraction": round(med(["extraction", "flows_per_s"]), 1),
            "cpu_pct_mean_of_one_core": round(
                med(["end_to_end", "resources", "cpu_pct_mean_of_one_core"]), 1),
            "rss_mb_peak": round(med(["end_to_end", "resources", "rss_mb_peak"]), 1),
        }
        latency = summarize_latencies(all_latency_samples)
        latency["n"] = int(len(all_latency_samples))
        latency["flows_timed"] = int(len(all_latency_samples))
        latency["batch_size"] = 1
        latency["note"] = ("percentiles sobre las muestras POOL de todas las "
                           "repeticiones (mejor estimación de la cola)")
        e2e = dict(e2e)
        e2e.update({k: summary[k] for k in (
            "flows_per_s_end_to_end", "flows_per_s_pcap_to_scores",
            "flows_per_s_infer_only")})
        extract = dict(extract)
        extract["flows_per_s"] = summary["flows_per_s_extraction"]
        print(f"\n[bench] mediana de {len(runs)} repeticiones: "
              f"{summary['flows_per_s_end_to_end']} flujos/s e2e, "
              f"p99 {latency['p99_ms']:.3f} ms")

    load_after = load_average()
    contaminated = load_before["1m"] > (os.cpu_count() or 1) * 0.9 or \
                   load_after["1m"] > (os.cpu_count() or 1) * 0.9
    if contaminated:
        print(f"[bench] AVISO: load 1m antes={load_before['1m']} despues={load_after['1m']} "
              f"con {os.cpu_count()} cores. La medida puede estar contaminada por otros "
              f"procesos; el JSON lo marca en load_average.contaminated=true.")

    stamp = datetime.now(timezone.utc).astimezone()
    result = {
        "benchmark": "bench_throughput",
        "generated_at": stamp.isoformat(),
        "hardware": hardware_info(),
        "load_average": {
            "before": load_before,
            "after": load_after,
            "nproc": os.cpu_count(),
            "contaminated": bool(contaminated),
        },
        "config": {
            "flows_requested": args.flows,
            "latency_flows": args.latency_flows,
            "batch_size": args.batch_size,
            "seed": args.seed,
            "model_path": str(args.model),
        },
        "model": model_meta,
        "repeats": summary if summary else 1,
        "extraction": extract,
        "pcap_io": io_stats,
        "extraction_unbuilt_packets": unbuilt,
        "inference_latency_per_flow": latency,
        "end_to_end": e2e,
        "excluded_from_measurement": [
            "NIC real, captura en vivo (tcpdump/af_packet), drops del kernel y Gbps de red",
            "latencia de red / tiempo entre llegada del paquete y scoring",
            "colas del agente, postfilter, escritura en hub (fuera del pipeline medido)",
            "zero-copy / DPDK / XDP: el pipeline usa Scapy en espacio de usuario",
        ],
        "no_medido": [
            "Gbps de red sostenidos: NO MEDIDO — no hay NIC dedicada ni permisos de "
            "captura en esta máquina virtual (QEMU), y una captura en loopback "
            "mediría la pila local, no el producto",
            "drops de captura del kernel: NO MEDIDO — requiere af_packet con "
            "privilegios y una NIC real",
            "throughput con el modelo desplegado en producción: NO MEDIDO — "
            "models/qivae.pkl no está publicado en el repo; se usa uno entrenado aquí",
            "throughput bajo concurrencia multi-flujo/multi-hilo: NO MEDIDO — el "
            "pipeline medido es de un solo proceso y un solo hilo de inferencia",
        ],
    }

    out = args.out or (REPORTS_DIR / f"bench-throughput-{stamp.strftime('%Y-%m-%dT%H-%M-%S')}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    latest = REPORTS_DIR / "bench-throughput-latest.json"
    with open(latest, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)

    print(f"\n[bench] JSON crudo: {out}")
    print(f"[bench] copia estable: {latest}")
    print("\n[bench] RESUMEN DEFENDIBLE")
    print(f"  flujos/s pcap -> scores (solo lectura): {e2e['flows_per_s_pcap_to_scores']}")
    print(f"  flujos/s extracción + inferencia   : {e2e['flows_per_s_end_to_end']}")
    print(f"  flujos/s solo inferencia (lotes)   : {e2e['flows_per_s_infer_only']}")
    print(f"  flujos/s solo extracción           : {extract['flows_per_s']}")
    if not latency.get("skipped"):
        print(f"  latencia por flujo p50/p95/p99: "
              f"{latency['p50_ms']:.3f} / {latency['p95_ms']:.3f} / {latency['p99_ms']:.3f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
