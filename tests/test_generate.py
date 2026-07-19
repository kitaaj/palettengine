"""Tests for harmony, scoring, and the generation engine."""

from __future__ import annotations

import random

import pytest

from palette_generator.color import contrast_ratio
from palette_generator.generate import generate, score
from palette_generator.generate.scorer import score_breakdown
from palette_generator.harmony import resolve_scheme, scheme_hues
from palette_generator.model import Color, Palette


# --------------------------------------------------------------------------- #
# harmony
# --------------------------------------------------------------------------- #
def test_scheme_hues_offsets() -> None:
    hues = scheme_hues("complementary", 30.0)
    assert hues == pytest.approx([30.0, 210.0])


def test_scheme_hues_wraps() -> None:
    hues = scheme_hues("triadic", 300.0)
    assert hues == pytest.approx([300.0, 60.0, 180.0])


def test_unknown_scheme_raises() -> None:
    with pytest.raises(ValueError):
        scheme_hues("nope", 0.0)


def test_resolve_auto_is_deterministic() -> None:
    a = resolve_scheme("auto", random.Random(7))
    b = resolve_scheme("auto", random.Random(7))
    assert a == b


# --------------------------------------------------------------------------- #
# engine: determinism, size, locks, base
# --------------------------------------------------------------------------- #
def test_determinism() -> None:
    a = generate(seed=42).hexes()
    b = generate(seed=42).hexes()
    assert a == b


def test_different_seeds_differ() -> None:
    a = generate(seed=1).hexes()
    b = generate(seed=2).hexes()
    assert a != b


@pytest.mark.parametrize("size", [1, 2, 3, 5, 8])
def test_size_respected(size: int) -> None:
    assert len(generate(seed=0, size=size)) == size


def test_size_zero_raises() -> None:
    with pytest.raises(ValueError):
        generate(size=0)


def test_hard_lock_is_exact() -> None:
    palette = generate(seed=3, size=5, locks={2: "#123456"})
    assert palette[2].hex == "#123456"


def test_base_is_pinned_at_slot_zero() -> None:
    palette = generate(seed=3, size=5, base="#3b82f6")
    assert palette[0].hex == "#3b82f6"


def test_base_lock_can_be_overridden_by_explicit_lock() -> None:
    palette = generate(seed=3, size=5, base="#3b82f6", locks={0: "#000000"})
    assert palette[0].hex == "#000000"


def test_lock_out_of_range_raises() -> None:
    with pytest.raises(ValueError):
        generate(size=3, locks={5: "#000000"})


def test_all_colors_in_gamut() -> None:
    from palette_generator.color import in_gamut

    for c in generate(seed=11, size=6):
        assert in_gamut(c.rgb)


# --------------------------------------------------------------------------- #
# scorer
# --------------------------------------------------------------------------- #
def test_duplicate_colors_score_low_on_distinctness() -> None:
    dup = [Color.from_hex("#ff0000"), Color.from_hex("#ff0000")]
    assert score_breakdown(dup)["distinctness"] == pytest.approx(0.0)


def test_spread_palette_beats_flat_palette() -> None:
    spread = [Color.from_hex(h) for h in ("#111111", "#8888ff", "#ffffff")]
    flat = [Color.from_hex(h) for h in ("#7a7a7a", "#808080", "#868686")]
    assert score(spread) > score(flat)


def test_ui_mode_adds_contrast_term() -> None:
    colors = list(generate(seed=5, mode="ui"))
    assert "contrast" in score_breakdown(colors, "ui")
    assert "contrast" not in score_breakdown(colors, "general")


def test_ui_mode_yields_a_usable_contrast_pair() -> None:
    # A UI palette should contain at least one AA-passing (>=4.5) text/bg pair.
    colors = list(generate(seed=5, mode="ui", size=5))
    rgbs = [c.rgb for c in colors]
    best = max(
        contrast_ratio(rgbs[i], rgbs[j])
        for i in range(len(rgbs))
        for j in range(i + 1, len(rgbs))
    )
    assert best >= 4.5


# --------------------------------------------------------------------------- #
# model
# --------------------------------------------------------------------------- #
def test_palette_repr_and_hexes() -> None:
    p = Palette([Color.from_hex("#ff0000"), Color.from_hex("#00ff00")])
    assert p.hexes() == ["#ff0000", "#00ff00"]
    assert "#ff0000" in repr(p)
