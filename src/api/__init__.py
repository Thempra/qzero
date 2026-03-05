"""Módulo de API REST."""

import sys
from pathlib import Path
import importlib.util

# Importar directamente desde el archivo .py
api_file = Path(__file__).parent.parent / "api.py"
spec = importlib.util.spec_from_file_location("api", api_file)
api_module = importlib.util.module_from_spec(spec)
sys.modules['src.api.api'] = api_module
spec.loader.exec_module(api_module)

create_app = api_module.create_app
start_server = api_module.start_server

__all__ = ['create_app', 'start_server']