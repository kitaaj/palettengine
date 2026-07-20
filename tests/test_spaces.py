"""Tests for color space conversions: known values, round-trips, and gamut clamping."""

from __future__ import annotations

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from palettengine.color import spaces as s


# --------------------------------------------------------------------------- #
# hex parsing / formatting
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("#000000", (0.0, 0.0, 0.0)),
        ("#ffffff", (1.0, 1.0, 1.0)),
        ("#ff0000", (1.0, 0.0, 0.0)),
        ("fff", (1.0, 1.0, 1.0)),
        ("#abc", (0xAA / 255, 0xBB / 255, 0xCC / 255)),
    ],
)
def test_hex_to_rgb(text: str, expected: s.RGB) -> None:
    assert s.hex_to_rgb(text) == pytest.approx(expected)


@pytest.mark.parametrize("bad", ["", "#12", "#12345", "wxyz12", "#gggggg"])
def test_hex_to_rgb_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        s.hex_to_rgb(bad)


def test_rgb_to_hex_clamps() -> None:
    assert s.rgb_to_hex((1.5, -0.2, 0.5)) == "#ff0080"
    assert s.rgb_to_hex((0.0, 0.0, 0.0)) == "#000000"


@given(st.integers(0, 255), st.integers(0, 255), st.integers(0, 255))
def test_hex_roundtrip_8bit(r: int, g: int, b: int) -> None:
    hexstr = f"#{r:02x}{g:02x}{b:02x}"
    assert s.rgb_to_hex(s.hex_to_rgb(hexstr)) == hexstr


# --------------------------------------------------------------------------- #
# OKLab reference values (Ottosson's published sRGB test vectors)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("hexstr", "L", "a", "b"),
    [
        ("#ffffff", 1.0, 0.0, 0.0),
        ("#000000", 0.0, 0.0, 0.0),
        ("#ff0000", 0.6279, 0.2249, 0.1258),
        ("#00ff00", 0.8664, -0.2339, 0.1795),
        ("#0000ff", 0.4520, -0.0324, -0.3115),
    ],
)
def test_rgb_to_oklab_reference(hexstr: str, L: float, a: float, b: float) -> None:
    got = s.rgb_to_oklab(s.hex_to_rgb(hexstr))
    assert got == pytest.approx((L, a, b), abs=1e-3)


# --------------------------------------------------------------------------- #
# round-trips
# --------------------------------------------------------------------------- #
rgb_channels = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


@given(rgb_channels, rgb_channels, rgb_channels)
def test_oklab_roundtrip(r: float, g: float, b: float) -> None:
    rgb = (r, g, b)
    back = s.oklab_to_rgb(s.rgb_to_oklab(rgb))
    assert back == pytest.approx(rgb, abs=5e-6)


@given(rgb_channels, rgb_channels, rgb_channels)
def test_oklch_roundtrip(r: float, g: float, b: float) -> None:
    rgb = (r, g, b)
    back = s.oklch_to_rgb(s.rgb_to_oklch(rgb))
    assert back == pytest.approx(rgb, abs=5e-6)


@given(rgb_channels, rgb_channels, rgb_channels)
def test_hsl_roundtrip(r: float, g: float, b: float) -> None:
    rgb = (r, g, b)
    back = s.hsl_to_rgb(s.rgb_to_hsl(rgb))
    assert back == pytest.approx(rgb, abs=1e-9)


@given(rgb_channels)
def test_srgb_linear_roundtrip(c: float) -> None:
    # The sRGB piecewise transfer function is not perfectly continuous at its joint,
    # so the round-trip carries ~1e-7 error near the threshold — far below 8-bit precision.
    assert s.linear_to_srgb(s.srgb_to_linear(c)) == pytest.approx(c, abs=1e-6)


# --------------------------------------------------------------------------- #
# OKLCH structure and gamut clamping
# --------------------------------------------------------------------------- #
def test_grey_has_zero_chroma() -> None:
    for v in (0.1, 0.5, 0.9):
        _L, C, _H = s.rgb_to_oklch((v, v, v))
        assert pytest.approx(0.0, abs=1e-6) == C


def test_clamp_in_gamut_is_noop() -> None:
    lch = s.rgb_to_oklch((0.4, 0.6, 0.2))
    assert s.clamp_oklch_to_gamut(lch) == pytest.approx(lch)


def test_clamp_reduces_chroma_and_stays_in_gamut() -> None:
    # An absurdly high chroma at mid lightness is out of gamut; clamping must fix it
    # while preserving L and H.
    L, _C, H = s.rgb_to_oklch((1.0, 0.0, 0.0))
    clamped = s.clamp_oklch_to_gamut((L, 0.5, H))
    assert s.in_gamut(s.oklch_to_rgb(clamped))
    assert clamped[0] == pytest.approx(L)
    assert clamped[2] == pytest.approx(H)
    assert clamped[1] < 0.5


@given(
    st.floats(0.02, 0.98),
    st.floats(0.0, 0.6),
    st.floats(0.0, 360.0),
)
def test_clamp_always_yields_in_gamut(L: float, C: float, H: float) -> None:
    clamped = s.clamp_oklch_to_gamut((L, C, H))
    assert s.in_gamut(s.oklch_to_rgb(clamped))


def test_hue_is_normalized() -> None:
    _L, _C, H = s.rgb_to_oklch((0.2, 0.5, 0.7))
    assert 0.0 <= H < 360.0


def test_oklch_to_hex_is_gamut_safe() -> None:
    # Way-out-of-gamut request should still produce a valid, parseable hex.
    hexstr = s.oklch_to_hex((0.5, 0.9, 30.0))
    assert len(hexstr) == 7 and hexstr[0] == "#"
    assert not math.isnan(s.hex_to_rgb(hexstr)[0])
