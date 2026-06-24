"""
terminal - CLI interface for the steganographic memory system.

The 'datassci terminal' - interactive command-line interface
to interact with nodes, probes, the memory matrix, and AI agents.
"""

from .cli import StegoTerminal, main

__all__ = ["StegoTerminal", "main"]
