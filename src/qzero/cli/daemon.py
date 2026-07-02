#!/usr/bin/env python3
"""
Módulo de gestión de daemon para QZero
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class DaemonManager:
    """Gestor de demonio para tareas autónomas de QZero"""

    def __init__(self):
        """Inicializa el gestor"""
        self.pid_file = Path.home() / ".qzero" / "qzero.pid"
        self.log_file = Path.home() / ".qzero" / "qzero.log"
        self.daemon_dir = Path.home() / ".qzero" / "daemon"

        self.daemon_dir.mkdir(parents=True, exist_ok=True)

    def _write_pid(self, pid: int):
        """Escribe el PID en el archivo"""
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, 'w') as f:
            f.write(str(pid))

    def _read_pid(self) -> Optional[int]:
        """Lee el PID del archivo"""
        if self.pid_file.exists():
            try:
                return int(self.pid_file.read_text())
            except ValueError:
                return None
        return None

    def _is_running(self, pid: int) -> bool:
        """Verifica si el proceso está corriendo"""
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False

    def start(self, interval: int = 60):
        """
        Inicia el daemon.

        Args:
            interval: Intervalo de chequeo en segundos
        """
        # Verificar si ya está corriendo
        pid = self._read_pid()
        if pid and self._is_running(pid):
            print(f"⚠️  QZero daemon ya está corriendo con PID: {pid}")
            return

        print("🚀 Iniciando QZero daemon...")

        # Crear proceso en background
        import subprocess

        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "qzero.cli.daemon_runner", str(interval)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            self._write_pid(process.pid)
            print(f"✅ QZero daemon iniciado con PID: {process.pid}")

            # Mostrar estado inicial
            time.sleep(1)
            self.status()

        except Exception as e:
            print(f"❌ Error al iniciar daemon: {e}", file=sys.stderr)
            raise

    def stop(self):
        """Detiene el daemon"""
        pid = self._read_pid()
        if not pid:
            print("⚠️  QZero daemon no está corriendo")
            return

        if not self._is_running(pid):
            print(f"⚠️  No se encontró proceso con PID: {pid}")
            self.pid_file.unlink(missing_ok=True)
            return

        try:
            print(f"🛑 Deteniendo QZero daemon (PID: {pid})...")
            os.kill(pid, 9)  # SIGKILL
            self.pid_file.unlink(missing_ok=True)
            print("✅ QZero daemon detenido")
        except ProcessLookupError:
            print(f"⚠️  Proceso con PID {pid} ya terminó")
            self.pid_file.unlink(missing_ok=True)
        except Exception as e:
            print(f"❌ Error al detener daemon: {e}", file=sys.stderr)

    def status(self):
        """Muestra el estado del daemon"""
        pid = self._read_pid()
        if not pid:
            print("⚠️  QZero daemon no está corriendo")
            return

        if self._is_running(pid):
            print(f"✅ QZero daemon está corriendo (PID: {pid})")

            # Mostrar actividad reciente
            if self.log_file.exists():
                try:
                    lines = self.log_file.read_text().split('\n')[-20:]
                    print(f"\n📝 Última actividad:")
                    for line in lines:
                        if line.strip():
                            print(f"   {line}")
                except Exception:
                    pass
        else:
            print(f"⚠️  PID {pid} no corresponde a un proceso activo")
            self.pid_file.unlink(missing_ok=True)


def daemon_runner(interval: int = 60):
    """Función ejecutada por el daemon"""
    import signal
    import random

    # Configurar signal handlers
    def signal_handler(sig, frame):
        print(f"\n⚠️  Signal recibido: {sig}, deteniendo daemon...")
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger = logging.getLogger(__name__)
    logger.info("QZero daemon iniciado")

    cycle_count = 0

    try:
        while True:
            cycle_count += 1
            logger.info(f" ciclo #{cycle_count}")

            # TODO: Ejecutar tareas autónomas
            # - Code Quality Monitor
            # - QZero Data Quality Monitor
            # - Daily Executive Summary
            # - Anomaly Risk Monitor

            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("QZero daemon detenido por usuario")
    except Exception as e:
        logger.error(f"Error en daemon: {e}")
        raise


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: daemon_runner <interval>")
        sys.exit(1)

    interval = int(sys.argv[1])
    daemon_runner(interval)