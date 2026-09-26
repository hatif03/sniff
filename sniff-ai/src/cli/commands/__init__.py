"""
sniff CLI Commands

Available commands:
- preflight: Validate Gemini/k2-horizon/Jev configuration
- init: Initialize sniff configuration
- run: Launch autonomous test run
- report: Display run summary
- personas: Manage persona profiles
- alert: Test Slack alert integration
- demo: Run deterministic demo mode
- experiment: Run experiments with multiple personas
"""

from . import init, personas, run, report, alert, demo, preflight, experiment

__all__ = ["init", "personas", "run", "report", "alert", "demo", "preflight", "experiment"]
