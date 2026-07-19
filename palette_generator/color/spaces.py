"""Color space conversions.

All internal color math in this project happens in perceptually-uniform OKLab / OKLCH.
sRGB and hex are treated as edge formats: parse on input, clamp to gamut on output.

Conventions
-----------
- ``RGB``   : tuple ``(r, g, b)`` of floats in ``[0, 1]`` (gamma-encoded sRGB).
- ``OKLab`` : tuple ``(L, a, b)``; ``L`` in ``[0, 1]``, ``a``/``b`` roughly ``[-0.4, 0.4]``.
- ``OKLCH`` : tuple ``(L, C, H)``; ``L`` in ``[0, 1]``, ``C`` >= 0, ``H`` in degrees ``[0, 360)``.
- ``HSL``   : tuple ``(H, S, L)``; ``H`` in degrees, ``S``/``L`` in ``[0, 1]``.
- 8-bit RGB: tuple ``(r, g, b)`` of ints in ``[0, 255]``.

OKLab conversion constants are from Björn Ottosson's reference implementation
(https://bottosson.github.io/posts/oklab/).
"""

from __future__ import annotations

import math

RGB = tuple[float, float, float]
OKLab = tuple[float, float, float]
OKLCH = tuple[float, float, float]
HSL = tuple[float, float, float]
RGB8 = tuple[int, int, int]

__all__ = [
    "RGB",
    "OKLab",
    "OKLCH",
    "HSL",
    "RGB8",
    "clamp",
    "hex_to_rgb",
    "rgb_to_hex",
    "rgb_to_rgb8",
    "rgb8_to_rgb",
    "srgb_to_linear",
    "linear_to_srgb",
    "rgb_to_linear",
    "linear_to_rgb",
    "linear_to_oklab",
    "oklab_to_linear",
    "rgb_to_oklab",
    "oklab_to_rgb",
    "oklab_to_oklch",
    "oklch_to_oklab",
    "rgb_to_oklch",
    "oklch_to_rgb",
    "rgb_to_hsl",
    "hsl_to_rgb",
    "in_gamut",
    "clamp_oklch_to_gamut",
    "hex_to_oklch",
    "oklch_to_hex",
]


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp ``x`` to the inclusive range ``[lo, hi]``."""
    return lo if x < lo else hi if x > hi else x


# --------------------------------------------------------------------------- #
# hex <-> rgb <-> 8-bit
# --------------------------------------------------------------------------- #
def hex_to_rgb(value: str) -> RGB:
    """Parse ``#rgb`` / ``#rrggbb`` (``#`` optional) into an sRGB float tuple."""
    h = value.lstrip("#").strip()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"invalid hex color: {value!r}")
    try:
        r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError as exc:  # non-hex characters
        raise ValueError(f"invalid hex color: {value!r}") from exc
    return (r / 255.0, g / 255.0, b / 255.0)


def rgb_to_rgb8(rgb: RGB) -> RGB8:
    """Quantize an sRGB float tuple to 8-bit ints, clamping out-of-gamut values."""
    return tuple(round(clamp(c) * 255) for c in rgb)  # type: ignore[return-value]


def rgb8_to_rgb(rgb8: RGB8) -> RGB:
    """Convert 8-bit ints to an sRGB float tuple."""
    r, g, b = rgb8
    return (r / 255.0, g / 255.0, b / 255.0)


def rgb_to_hex(rgb: RGB) -> str:
    """Format an sRGB float tuple as ``#rrggbb`` (clamped to gamut)."""
    r, g, b = rgb_to_rgb8(rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


# --------------------------------------------------------------------------- #
# sRGB gamma <-> linear
# --------------------------------------------------------------------------- #
def srgb_to_linear(c: float) -> float:
    """Linearize a single gamma-encoded sRGB channel in ``[0, 1]``."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    """Gamma-encode a single linear channel back to sRGB."""
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def rgb_to_linear(rgb: RGB) -> RGB:
    r, g, b = rgb
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b))


def linear_to_rgb(lin: RGB) -> RGB:
    r, g, b = lin
    return (linear_to_srgb(r), linear_to_srgb(g), linear_to_srgb(b))


# --------------------------------------------------------------------------- #
# linear sRGB <-> OKLab
# --------------------------------------------------------------------------- #
def linear_to_oklab(lin: RGB) -> OKLab:
    r, g, b = lin
    lp = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    mp = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    sp = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    l_ = math.copysign(abs(lp) ** (1 / 3), lp)
    m_ = math.copysign(abs(mp) ** (1 / 3), mp)
    s_ = math.copysign(abs(sp) ** (1 / 3), sp)

    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_linear(lab: OKLab) -> RGB:
    L, a, b = lab
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b

    lc = l_ * l_ * l_
    mc = m_ * m_ * m_
    sc = s_ * s_ * s_

    return (
        4.0767416621 * lc - 3.3077115913 * mc + 0.2309699292 * sc,
        -1.2684380046 * lc + 2.6097574011 * mc - 0.3413193965 * sc,
        -0.0041960863 * lc - 0.7034186147 * mc + 1.7076147010 * sc,
    )


def rgb_to_oklab(rgb: RGB) -> OKLab:
    return linear_to_oklab(rgb_to_linear(rgb))


def oklab_to_rgb(lab: OKLab) -> RGB:
    return linear_to_rgb(oklab_to_linear(lab))


# --------------------------------------------------------------------------- #
# OKLab <-> OKLCH  (cartesian <-> polar in the a/b plane)
# --------------------------------------------------------------------------- #
def oklab_to_oklch(lab: OKLab) -> OKLCH:
    L, a, b = lab
    C = math.hypot(a, b)
    H = math.degrees(math.atan2(b, a)) % 360.0
    return (L, C, H)


def oklch_to_oklab(lch: OKLCH) -> OKLab:
    L, C, H = lch
    rad = math.radians(H)
    return (L, C * math.cos(rad), C * math.sin(rad))


def rgb_to_oklch(rgb: RGB) -> OKLCH:
    return oklab_to_oklch(rgb_to_oklab(rgb))


def oklch_to_rgb(lch: OKLCH) -> RGB:
    return oklab_to_rgb(oklch_to_oklab(lch))


# --------------------------------------------------------------------------- #
# HSL (convenience / legacy interop)
# --------------------------------------------------------------------------- #
def rgb_to_hsl(rgb: RGB) -> HSL:
    r, g, b = rgb
    mx, mn = max(r, g, b), min(r, g, b)
    L = (mx + mn) / 2.0
    if mx == mn:
        return (0.0, 0.0, L)
    d = mx - mn
    S = d / (2.0 - mx - mn) if L > 0.5 else d / (mx + mn)
    if mx == r:
        H = (g - b) / d + (6.0 if g < b else 0.0)
    elif mx == g:
        H = (b - r) / d + 2.0
    else:
        H = (r - g) / d + 4.0
    return (H * 60.0, S, L)


def hsl_to_rgb(hsl: HSL) -> RGB:
    H, S, L = hsl
    if S == 0:
        return (L, L, L)
    q = L * (1 + S) if L < 0.5 else L + S - L * S
    p = 2 * L - q
    h = (H / 360.0) % 1.0

    def hue(t: float) -> float:
        t %= 1.0
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    return (hue(h + 1 / 3), hue(h), hue(h - 1 / 3))


# --------------------------------------------------------------------------- #
# gamut
# --------------------------------------------------------------------------- #
def in_gamut(rgb: RGB, eps: float = 1e-4) -> bool:
    """True if every channel is within ``[0, 1]`` (up to ``eps`` tolerance)."""
    return all(-eps <= c <= 1.0 + eps for c in rgb)


def clamp_oklch_to_gamut(lch: OKLCH, eps: float = 1e-4) -> OKLCH:
    """Reduce chroma until the color fits in sRGB, preserving lightness and hue.

    This is the perceptually-honest way to bring an out-of-gamut OKLCH color back
    into sRGB: rather than clipping RGB channels (which shifts hue), we binary-search
    the largest chroma that stays in gamut at the given ``L`` and ``H``.
    """
    L, C, H = lch
    if L <= 0.0:
        return (0.0, 0.0, H)
    if L >= 1.0:
        return (1.0, 0.0, H)
    if in_gamut(oklch_to_rgb(lch), eps):
        return lch

    lo, hi = 0.0, C
    for _ in range(24):  # ~1e-7 chroma precision, plenty for 8-bit output
        mid = (lo + hi) / 2.0
        if in_gamut(oklch_to_rgb((L, mid, H)), eps):
            lo = mid
        else:
            hi = mid
    return (L, lo, H)


# --------------------------------------------------------------------------- #
# convenience round-trips through hex, gamut-safe
# --------------------------------------------------------------------------- #
def hex_to_oklch(value: str) -> OKLCH:
    return rgb_to_oklch(hex_to_rgb(value))


def oklch_to_hex(lch: OKLCH) -> str:
    """OKLCH -> ``#rrggbb``, first reducing chroma to fit the sRGB gamut."""
    return rgb_to_hex(oklch_to_rgb(clamp_oklch_to_gamut(lch)))
