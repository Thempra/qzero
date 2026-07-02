#!/usr/bin/env python3
"""
QZero legacy entry-point — delegates to the installed CLI.

Prefer the installed command: ``qzero --help``
"""
from qzero.cli import main

if __name__ == "__main__":
    main()
