"""QZero Agent package.

A lightweight, deployable agent that runs on ANY server, captures live
network traffic, analyzes it in real-time with QZero's quantum models, and
pushes detected alerts to a central QZero hub for centralised reflection.

Designed to be dependency-light (stdlib urllib for transport) so it can be
dropped onto any host with just the qzero package + scapy.
"""

from .agent import QZeroAgent, AgentConfig

__all__ = ["QZeroAgent", "AgentConfig"]
