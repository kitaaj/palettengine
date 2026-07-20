"""Palette generation: the deterministic engine and its quality scorer."""

from .engine import generate
from .scorer import score, score_breakdown

__all__ = ["generate", "score", "score_breakdown"]
