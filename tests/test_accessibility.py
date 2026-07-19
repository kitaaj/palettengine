"""Tests for WCAG auto-fix and CVD simulation."""

from __future__ import annotations

import pytest

from palette_generator.accessibility import (
    CVD_KINDS,
    auto_fix,
    best_text_color,
    contrast_matrix,
    simulate,
    simulate_palette,
)
from palette_generator.color import contrast_ratio, passes_wcag
from palette_generator.model import Color, Palette


def _c(h: str) -> Color:
    return Color.from_hex(h)


def test_contrast_matrix_shape_and_diagonal() -> None:
    p = Palette([_c("#000000"), _c("#ffffff"), _c("#ff0000")])
    m = contrast_matrix(p)
    assert len(m) == 3 and all(len(row) == 3 for row in m)
    for i in range(3):
        assert m[i][i] == pytest.approx(1.0)
    assert m[0][1] == pytest.approx(21.0, abs=1e-6)


def test_best_text_color_picks_highest_contrast() -> None:
    bg = _c("#ffffff")
    assert best_text_color(bg, [_c("#eeeeee"), _c("#111111"), _c("#999999")]).hex == "#111111"


def test_auto_fix_makes_pair_pass_aa() -> None:
    bg = _c("#ffffff")
    fg = _c("#bbbbbb")  # fails AA on white
    assert not passes_wcag(fg.rgb, bg.rgb, "AA")
    fixed = auto_fix(fg, bg, "AA")
    assert passes_wcag(fixed.rgb, bg.rgb, "AA")


def test_auto_fix_preserves_hue() -> None:
    bg = _c("#ffffff")
    fg = Color.from_oklch(0.75, 0.12, 30.0)
    fixed = auto_fix(fg, bg, "AA")
    assert pytest.approx(30.0, abs=1.0) == fixed.H


def test_auto_fix_noop_when_already_passing() -> None:
    bg = _c("#ffffff")
    fg = _c("#000000")
    assert auto_fix(fg, bg, "AA") is fg


def test_auto_fix_unreachable_returns_best_effort() -> None:
    # AAA (7:1) is unreachable against a mid grey; result should still be the max contrast.
    bg = _c("#808080")
    fg = _c("#7a7a7a")
    fixed = auto_fix(fg, bg, "AAA")
    # Best effort exceeds the starting contrast even if it can't hit 7:1.
    assert contrast_ratio(fixed.rgb, bg.rgb) > contrast_ratio(fg.rgb, bg.rgb)


@pytest.mark.parametrize("kind", CVD_KINDS)
def test_simulate_returns_valid_rgb(kind: str) -> None:
    out = simulate((0.8, 0.1, 0.1), kind)
    assert all(0.0 <= c <= 1.0 for c in out)


def test_simulate_unknown_kind_raises() -> None:
    with pytest.raises(ValueError):
        simulate((0.5, 0.5, 0.5), "nope")


def test_simulate_greyscale_is_stable() -> None:
    # Achromatic colors are (near-)unchanged under CVD simulation.
    grey = (0.5, 0.5, 0.5)
    for kind in CVD_KINDS:
        out = simulate(grey, kind)
        assert out == pytest.approx(grey, abs=0.02)


def test_simulate_palette_preserves_length() -> None:
    p = Palette([_c("#ff0000"), _c("#00ff00"), _c("#0000ff")])
    assert len(simulate_palette(p, "deutan")) == 3
