"""Palette serializers.

Each ``to_*`` function takes a :class:`~palettengine.model.Palette` and an optional
``roles`` mapping (from :func:`palettengine.roles.assign_roles`). When roles are given,
named entries (``--color-primary`` etc.) are emitted alongside the indexed swatches.

Text formats return ``str``; binary formats (ASE) return ``bytes``. Use :func:`export`
to dispatch by name.
"""

from __future__ import annotations

import json
import struct
from collections.abc import Callable

from ..color import clamp
from ..model import Color, Palette

__all__ = [
    "to_json",
    "to_css",
    "to_scss",
    "to_tailwind",
    "to_tokens",
    "to_svg",
    "to_gpl",
    "to_ase",
    "export",
    "TEXT_FORMATS",
    "BINARY_FORMATS",
    "FORMATS",
]

Roles = dict[str, Color] | None


def _entries(palette: Palette, roles: Roles) -> list[tuple[str, Color]]:
    """Ordered (name, color) pairs: indexed swatches first, then named roles."""
    out: list[tuple[str, Color]] = [(f"color-{i + 1}", c) for i, c in enumerate(palette)]
    if roles:
        out.extend((name, color) for name, color in roles.items())
    return out


# --------------------------------------------------------------------------- #
# text formats
# --------------------------------------------------------------------------- #
def to_json(palette: Palette, roles: Roles = None) -> str:
    doc: dict[str, object] = {
        "colors": [
            {"hex": c.hex, "oklch": [round(v, 4) for v in c.oklch]} for c in palette
        ]
    }
    if roles:
        doc["roles"] = {name: color.hex for name, color in roles.items()}
    return json.dumps(doc, indent=2)


def to_css(palette: Palette, roles: Roles = None) -> str:
    lines = [":root {"]
    lines += [f"  --{name}: {color.hex};" for name, color in _entries(palette, roles)]
    lines.append("}")
    return "\n".join(lines)


def to_scss(palette: Palette, roles: Roles = None) -> str:
    return "\n".join(f"${name}: {color.hex};" for name, color in _entries(palette, roles))


def to_tailwind(palette: Palette, roles: Roles = None) -> str:
    colors = {name: color.hex for name, color in _entries(palette, roles)}
    body = json.dumps(colors, indent=6)
    # Re-indent the closing brace to sit under the key.
    body = body[:-1] + "    }"
    return (
        "/** tailwind.config.js */\n"
        "module.exports = {\n"
        "  theme: {\n"
        "    extend: {\n"
        f"      colors: {body},\n"
        "    },\n"
        "  },\n"
        "};\n"
    )


def to_tokens(palette: Palette, roles: Roles = None) -> str:
    """W3C Design Tokens (draft) format."""
    token_color: dict[str, dict[str, str]] = {
        name: {"$type": "color", "$value": color.hex}
        for name, color in _entries(palette, roles)
    }
    return json.dumps({"color": token_color}, indent=2)


def to_svg(palette: Palette, roles: Roles = None) -> str:
    sw, h, pad = 120, 140, 0
    entries = list(palette)
    width = sw * len(entries) or sw
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" '
        f'viewBox="0 0 {width} {h}">'
    ]
    for i, color in enumerate(entries):
        x = i * sw + pad
        # Label color: black or white for legibility on the swatch.
        from ..color import contrast_ratio

        label = "#000000" if contrast_ratio((0, 0, 0), color.rgb) >= 4.5 else "#ffffff"
        parts.append(f'<rect x="{x}" y="0" width="{sw}" height="{h}" fill="{color.hex}"/>')
        parts.append(
            f'<text x="{x + sw / 2}" y="{h - 16}" fill="{label}" '
            f'font-family="monospace" font-size="14" text-anchor="middle">{color.hex}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def to_gpl(palette: Palette, roles: Roles = None) -> str:
    """GIMP / Inkscape palette (.gpl)."""
    lines = ["GIMP Palette", "Name: palettengine", f"Columns: {len(palette) or 1}", "#"]
    for name, color in _entries(palette, roles):
        r, g, b = (round(clamp(v) * 255) for v in color.rgb)
        lines.append(f"{r:3d} {g:3d} {b:3d}\t{name} {color.hex}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# binary format: Adobe Swatch Exchange (.ase)
# --------------------------------------------------------------------------- #
def to_ase(palette: Palette, roles: Roles = None) -> bytes:
    """Adobe Swatch Exchange (.ase), RGB color entries."""
    entries = _entries(palette, roles)
    body = bytearray()
    for name, color in entries:
        r, g, b = (clamp(v) for v in color.rgb)
        block = bytearray()
        # Name: UTF-16BE, null-terminated; length is code-unit count incl. terminator.
        block += struct.pack(">H", len(name) + 1)
        block += name.encode("utf-16-be") + b"\x00\x00"
        block += b"RGB "
        block += struct.pack(">fff", r, g, b)
        block += struct.pack(">H", 2)  # color type: normal
        body += struct.pack(">H", 0x0001)  # block type: color entry
        body += struct.pack(">I", len(block))
        body += block
    header = b"ASEF" + struct.pack(">HH", 1, 0) + struct.pack(">I", len(entries))
    return bytes(header + body)


# --------------------------------------------------------------------------- #
# dispatch
# --------------------------------------------------------------------------- #
TEXT_FORMATS: dict[str, Callable[[Palette, Roles], str]] = {
    "json": to_json,
    "css": to_css,
    "scss": to_scss,
    "tailwind": to_tailwind,
    "tokens": to_tokens,
    "svg": to_svg,
    "gpl": to_gpl,
}
BINARY_FORMATS: dict[str, Callable[[Palette, Roles], bytes]] = {
    "ase": to_ase,
}
FORMATS: tuple[str, ...] = (*TEXT_FORMATS, *BINARY_FORMATS)


def export(palette: Palette, fmt: str, roles: Roles = None) -> str | bytes:
    """Serialize ``palette`` to ``fmt`` (see :data:`FORMATS`)."""
    if fmt in TEXT_FORMATS:
        return TEXT_FORMATS[fmt](palette, roles)
    if fmt in BINARY_FORMATS:
        return BINARY_FORMATS[fmt](palette, roles)
    raise ValueError(f"unknown format {fmt!r}; choose from {FORMATS}")
