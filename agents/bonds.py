"""Bonds specialist: a thin binding of the generic specialist to the 'bonds' manifest of the active domain."""

from agents.specialist import make_analyze

analyze = make_analyze("bonds")
