"""Tests for WCAG contrast and perceptual difference."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from palettengine.color import contrast as c
from palettengine.color import difference as d
from palettengine.color import spaces as s


def test_black_white_is_max_contrast() -> None:
    assert c.contrast_ratio_hex("#000000", "#ffffff") == pytest.approx(21.0, abs=1e-6)


def test_identical_colors_have_ratio_one() -> None:
    assert c.contrast_ratio_hex("#3b82f6", "#3b82f6") == pytest.approx(1.0, abs=1e-9)


def test_contrast_is_symmetric() -> None:
    a = c.contrast_ratio_hex("#123456", "#abcdef")
    b = c.contrast_ratio_hex("#abcdef", "#123456")
    assert a == pytest.approx(b)


def test_passes_wcag_levels() -> None:
    white, black = s.hex_to_rgb("#ffffff"), s.hex_to_rgb("#000000")
    assert c.passes_wcag(black, white, "AA")
    assert c.passes_wcag(black, white, "AAA")
    # A mid grey on white fails AA for normal text.
    grey = s.hex_to_rgb("#999999")
    assert not c.passes_wcag(grey, white, "AA")


def test_passes_wcag_unknown_level() -> None:
    with pytest.raises(ValueError):
        c.passes_wcag((0, 0, 0), (1, 1, 1), "AAAA")


@given(
    st.floats(0, 1),
    st.floats(0, 1),
    st.floats(0, 1),
    st.floats(0, 1),
    st.floats(0, 1),
    st.floats(0, 1),
)
def test_contrast_in_valid_range(
    r1: float, g1: float, b1: float, r2: float, g2: float, b2: float
) -> None:
    ratio = c.contrast_ratio((r1, g1, b1), (r2, g2, b2))
    assert 1.0 <= ratio <= 21.0 + 1e-9


def test_delta_e_zero_for_identical() -> None:
    assert d.delta_e_ok(s.hex_to_rgb("#abcdef"), s.hex_to_rgb("#abcdef")) == pytest.approx(0.0)


def test_delta_e_positive_for_different() -> None:
    assert d.delta_e_ok(s.hex_to_rgb("#000000"), s.hex_to_rgb("#ffffff")) > 0.9
