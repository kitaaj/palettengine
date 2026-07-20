"""Core data types: an immutable ``Color`` and a ``Palette`` of colors.

Colors are stored canonically in OKLCH (our working space) and converted to sRGB/hex
only at the edges, always gamut-clamped so ``.hex`` and ``.rgb`` are safe to use.
"""

from __future__ import annotations

from dataclasses import dataclass

from .color import (
    OKLCH,
    RGB,
    OKLab,
    clamp_oklch_to_gamut,
    hex_to_oklch,
    oklch_to_hex,
    oklch_to_oklab,
    oklch_to_rgb,
)

__all__ = ["Color", "Palette"]


@dataclass(frozen=True)
class Color:
    """A single color, stored in OKLCH ``(L, C, H)``."""

    oklch: OKLCH

    @classmethod
    def from_hex(cls, value: str) -> Color:
        return cls(hex_to_oklch(value))

    @classmethod
    def from_oklch(cls, L: float, C: float, H: float) -> Color:
        return cls((L, C, H))

    @property
    def L(self) -> float:
        return self.oklch[0]

    @property
    def C(self) -> float:
        return self.oklch[1]

    @property
    def H(self) -> float:
        return self.oklch[2]

    @property
    def gamut_safe(self) -> OKLCH:
        """This color's OKLCH with chroma reduced to fit inside sRGB."""
        return clamp_oklch_to_gamut(self.oklch)

    @property
    def rgb(self) -> RGB:
        return oklch_to_rgb(self.gamut_safe)

    @property
    def oklab(self) -> OKLab:
        return oklch_to_oklab(self.oklch)

    @property
    def hex(self) -> str:
        return oklch_to_hex(self.oklch)

    def __repr__(self) -> str:
        L, C, H = self.oklch
        return f"Color({self.hex} oklch({L:.3f} {C:.3f} {H:.1f}))"


@dataclass
class Palette:
    """An ordered collection of colors."""

    colors: list[Color]

    def hexes(self) -> list[str]:
        return [c.hex for c in self.colors]

    def __len__(self) -> int:
        return len(self.colors)

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.colors)

    def __getitem__(self, i: int) -> Color:
        return self.colors[i]

    def __repr__(self) -> str:
        return f"Palette({', '.join(self.hexes())})"
