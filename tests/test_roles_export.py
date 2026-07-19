"""Tests for semantic role assignment and exporters."""

from __future__ import annotations

import struct

import pytest

from palette_generator.color import passes_wcag
from palette_generator.export import FORMATS, export, to_ase, to_css, to_gpl, to_json
from palette_generator.model import Color, Palette
from palette_generator.roles import ROLE_ORDER, assign_roles


def _palette() -> Palette:
    return Palette(
        [Color.from_hex(h) for h in ("#0b132b", "#1c2541", "#3a506b", "#5bc0be", "#e0fbfc")]
    )


# --------------------------------------------------------------------------- #
# roles
# --------------------------------------------------------------------------- #
def test_assign_roles_has_all_roles() -> None:
    roles = assign_roles(_palette(), "light")
    assert set(roles) == set(ROLE_ORDER)


def test_light_theme_background_is_lightest() -> None:
    p = _palette()
    roles = assign_roles(p, "light")
    assert max(c.L for c in p) == roles["background"].L


def test_dark_theme_background_is_darkest() -> None:
    p = _palette()
    roles = assign_roles(p, "dark")
    assert min(c.L for c in p) == roles["background"].L


def test_text_is_readable_on_background() -> None:
    for theme in ("light", "dark"):
        roles = assign_roles(_palette(), theme)
        assert passes_wcag(roles["text"].rgb, roles["background"].rgb, "AA")


def test_assign_roles_bad_theme_raises() -> None:
    with pytest.raises(ValueError):
        assign_roles(_palette(), "sepia")


def test_assign_roles_empty_raises() -> None:
    with pytest.raises(ValueError):
        assign_roles(Palette([]), "light")


# --------------------------------------------------------------------------- #
# exporters
# --------------------------------------------------------------------------- #
def test_json_roundtrips() -> None:
    import json

    doc = json.loads(to_json(_palette()))
    assert len(doc["colors"]) == 5
    assert doc["colors"][0]["hex"].startswith("#")


def test_css_contains_vars_and_roles() -> None:
    p = _palette()
    css = to_css(p, assign_roles(p, "light"))
    assert "--color-1:" in css
    assert "--primary:" in css
    assert css.strip().endswith("}")


def test_gpl_header_and_rows() -> None:
    gpl = to_gpl(_palette())
    assert gpl.startswith("GIMP Palette")
    assert gpl.count("\t") == 5  # one tab per swatch row


def test_ase_is_wellformed() -> None:
    data = to_ase(_palette())
    assert data[:4] == b"ASEF"
    major, minor, count = struct.unpack(">HHI", data[4:12])
    assert (major, minor, count) == (1, 0, 5)


def test_ase_includes_roles_in_count() -> None:
    p = _palette()
    data = to_ase(p, assign_roles(p, "light"))
    count = struct.unpack(">I", data[8:12])[0]
    assert count == 5 + len(ROLE_ORDER)


@pytest.mark.parametrize("fmt", FORMATS)
def test_export_dispatch_all_formats(fmt: str) -> None:
    out = export(_palette(), fmt)
    assert isinstance(out, (str, bytes))
    assert len(out) > 0


def test_export_unknown_format_raises() -> None:
    with pytest.raises(ValueError):
        export(_palette(), "docx")
