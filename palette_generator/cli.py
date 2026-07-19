"""Command-line interface: ``palette generate ...``."""

from __future__ import annotations

import argparse
import contextlib
import sys

from .accessibility import CVD_KINDS, simulate_palette
from .color import contrast_ratio
from .export import BINARY_FORMATS, FORMATS, export
from .generate import generate, score, score_breakdown
from .harmony import SCHEMES
from .model import Color, Palette
from .roles import assign_roles

__all__ = ["main"]


def _parse_lock(spec: str) -> tuple[int, str]:
    """Parse a ``index:hexcolor`` lock spec."""
    try:
        idx_s, hexstr = spec.split(":", 1)
        return int(idx_s), hexstr
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid --lock {spec!r}; expected INDEX:HEX") from exc


def _swatch(color: Color, width: int = 6) -> str:
    """A truecolor ANSI block for a color, with a readable hex label overlaid."""
    r, g, b = (round(c * 255) for c in color.rgb)
    # Choose black or white text for legibility against the swatch.
    text_rgb = (0.0, 0.0, 0.0) if contrast_ratio((0, 0, 0), color.rgb) >= 4.5 else (1.0, 1.0, 1.0)
    tr, tg, tb = (round(c * 255) for c in text_rgb)
    label = color.hex.center(width)
    return f"\x1b[48;2;{r};{g};{b}m\x1b[38;2;{tr};{tg};{tb}m{label}\x1b[0m"


def _render(palette: Palette, mode: str, *, color: bool, explain: bool) -> str:
    lines: list[str] = []
    if color:
        lines.append("".join(_swatch(c) for c in palette))
    lines.append("  ".join(palette.hexes()))
    if explain:
        lines.append("")
        lines.append(f"score: {score(list(palette), mode):.3f}   (mode={mode})")
        for term, value in score_breakdown(list(palette), mode).items():
            bar = "█" * round(value * 20)
            lines.append(f"  {term:<16} {value:.2f} {bar}")
    return "\n".join(lines)


def _emit_export(args: argparse.Namespace, palette: Palette) -> None:
    roles = None if args.roles == "none" else assign_roles(palette, args.roles)
    data = export(palette, args.export, roles)
    if args.out:
        mode = "wb" if args.export in BINARY_FORMATS else "w"
        with open(args.out, mode) as fh:
            fh.write(data)
        print(f"wrote {args.export} -> {args.out}", file=sys.stderr)
    elif isinstance(data, bytes):
        sys.stdout.buffer.write(data)
    else:
        print(data)


def _emit(args: argparse.Namespace, palette: Palette) -> None:
    """Shared post-processing + output for generate and extract."""
    if args.simulate:
        palette = simulate_palette(palette, args.simulate)

    if args.export:
        _emit_export(args, palette)
        return

    if args.format == "hex":
        use_color = sys.stdout.isatty() and not args.no_color
        print(_render(palette, args.mode, color=use_color, explain=args.explain))
        if args.roles != "none":
            _print_roles(palette, args.roles, color=use_color)
    elif args.format == "list":
        for h in palette.hexes():
            print(h)
    elif args.format == "json":
        import json

        rows = [{"hex": c.hex, "oklch": [round(v, 4) for v in c.oklch]} for c in palette]
        doc: dict[str, object] = {"colors": rows}
        if args.roles != "none":
            doc["roles"] = {n: c.hex for n, c in assign_roles(palette, args.roles).items()}
        print(json.dumps(doc, indent=2))


def _cmd_generate(args: argparse.Namespace) -> int:
    locks = dict(_parse_lock(s) for s in args.lock) if args.lock else None
    palette = generate(
        base=args.base,
        scheme=args.scheme,
        size=args.size,
        locks=locks,
        seed=args.seed,
        mode=args.mode,
        candidates=args.candidates,
    )
    _emit(args, palette)
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    try:
        from . import extract as ex
    except ImportError as exc:  # numpy/Pillow not installed
        raise ValueError(
            f"extraction needs the [image] extra: pip install 'palette-generator[image]' ({exc})"
        ) from exc

    is_video = ex.is_video_path(args.source) if args.kind == "auto" else args.kind == "video"
    fn = ex.extract_video if is_video else ex.extract_image
    palette = fn(
        args.source,
        size=args.size,
        seed=args.seed,
        mode=args.mode,
        faithful=args.faithful,
        candidates=args.candidates,
    )
    _emit(args, palette)
    return 0


def _print_roles(palette: Palette, theme: str, *, color: bool) -> None:
    print(f"\nroles ({theme}):")
    for name, c in assign_roles(palette, theme).items():
        swatch = _swatch(c) + " " if color else ""
        print(f"  {swatch}{name:<12} {c.hex}")


def _add_output_args(p: argparse.ArgumentParser) -> None:
    """Output/post-processing options shared by generate and extract."""
    p.add_argument(
        "--format", default="hex", choices=["hex", "list", "json"], help="console output format"
    )
    p.add_argument(
        "--roles",
        default="none",
        choices=["none", "light", "dark"],
        help="assign semantic UI roles for a light/dark theme",
    )
    p.add_argument(
        "--export",
        choices=list(FORMATS),
        help="serialize to a design/dev format instead of the console view",
    )
    p.add_argument("--out", metavar="FILE", help="write --export output to a file")
    p.add_argument(
        "--simulate",
        choices=list(CVD_KINDS),
        help="preview the palette under a color-vision deficiency",
    )
    p.add_argument("--explain", action="store_true", help="show the quality score breakdown")
    p.add_argument("--no-color", action="store_true", help="disable ANSI swatches")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="palette", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="generate a color palette")
    g.add_argument("--base", help="base color as hex, e.g. '#3b82f6' (pinned into the palette)")
    g.add_argument(
        "--scheme",
        default="auto",
        choices=[*sorted(SCHEMES), "auto"],
        help="harmony scheme (default: auto)",
    )
    g.add_argument("--size", type=int, default=5, help="number of colors (default: 5)")
    g.add_argument("--mode", default="general", choices=["general", "ui"], help="generation mode")
    g.add_argument("--seed", type=int, default=None, help="RNG seed for reproducible output")
    g.add_argument(
        "--lock",
        action="append",
        default=[],
        metavar="INDEX:HEX",
        help="pin a slot to a color, e.g. --lock 0:#222222 (repeatable)",
    )
    g.add_argument("--candidates", type=int, default=240, help="candidates to sample")
    _add_output_args(g)
    g.set_defaults(func=_cmd_generate)

    e = sub.add_parser("extract", help="extract a palette from an image or video")
    e.add_argument("source", help="path to an image or video file")
    e.add_argument("--size", type=int, default=5, help="number of colors (default: 5)")
    e.add_argument("--mode", default="general", choices=["general", "ui"], help="scoring mode")
    e.add_argument("--seed", type=int, default=None, help="RNG seed for reproducible output")
    e.add_argument(
        "--kind",
        default="auto",
        choices=["auto", "image", "video"],
        help="treat source as image/video (default: auto-detect by extension)",
    )
    e.add_argument(
        "--faithful",
        action="store_true",
        help="return the most representative colors instead of the best-scoring palette",
    )
    e.add_argument("--candidates", type=int, default=300, help="candidate palettes to score")
    _add_output_args(e)
    e.set_defaults(func=_cmd_extract)
    return parser


def main(argv: list[str] | None = None) -> int:
    # Ensure ANSI swatches and the score bars render on legacy consoles (e.g. Windows cp1252).
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        with contextlib.suppress(ValueError, OSError):
            reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result: int = args.func(args)
    except (ValueError, argparse.ArgumentTypeError) as exc:
        parser.error(str(exc))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
