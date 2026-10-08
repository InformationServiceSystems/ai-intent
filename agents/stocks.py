"""Stocks specialist: a thin binding of the generic specialist to the 'stocks' manifest of the active domain."""

from agents.specialist import make_analyze

analyze = make_analyze("stocks")
