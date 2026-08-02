#!/usr/bin/env python3
"""Assemble mood-shell PNG frames into a palette-optimized GIF.

Keeps docs/media/mood-shell.gif under ~2–3 MB via resize + adaptive palette.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


def _blend(a: Image.Image, b: Image.Image, t: float) -> Image.Image:
    a_rgba = a.convert("RGBA")
    b_rgba = b.convert("RGBA")
    if a_rgba.size != b_rgba.size:
        b_rgba = b_rgba.resize(a_rgba.size, Image.Resampling.LANCZOS)
    return Image.blend(a_rgba, b_rgba, t)


def _to_gif_frame(im: Image.Image, max_width: int, colors: int) -> Image.Image:
    rgb = im.convert("RGB")
    if rgb.width > max_width:
        ratio = max_width / rgb.width
        rgb = rgb.resize(
            (max_width, max(1, int(rgb.height * ratio))),
            Image.Resampling.LANCZOS,
        )
    return rgb.convert(
        "P",
        palette=Image.Palette.ADAPTIVE,
        colors=max(16, min(256, colors)),
    )


def assemble(
    frames: list[Path],
    out: Path,
    *,
    hold_ms: int,
    fade_steps: int,
    max_width: int,
    colors: int,
) -> None:
    images = [Image.open(p).convert("RGBA") for p in frames]
    if not images:
        raise SystemExit("no frames")

    sequence: list[Image.Image] = []
    durations: list[int] = []
    fade_ms = max(40, hold_ms // max(fade_steps, 1))

    for i, im in enumerate(images):
        sequence.append(_to_gif_frame(im, max_width, colors))
        durations.append(hold_ms)
        nxt = images[(i + 1) % len(images)]
        if fade_steps > 0 and len(images) > 1:
            for s in range(1, fade_steps + 1):
                t = s / (fade_steps + 1)
                sequence.append(_to_gif_frame(_blend(im, nxt, t), max_width, colors))
                durations.append(fade_ms)

    out.parent.mkdir(parents=True, exist_ok=True)
    sequence[0].save(
        out,
        save_all=True,
        append_images=sequence[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )
    size = out.stat().st_size
    print(f"{out}: {size} bytes ({size / (1024 * 1024):.2f} MiB)", file=sys.stderr)
    if size > 3 * 1024 * 1024:
        print(
            "warning: GIF exceeds 3 MiB target — re-run with --max-width 560",
            file=sys.stderr,
        )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("frames", nargs="+", type=Path, help="PNG frame paths in order")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--hold-ms", type=int, default=1200)
    p.add_argument("--fade-steps", type=int, default=2)
    p.add_argument("--max-width", type=int, default=520)
    p.add_argument("--colors", type=int, default=64)
    args = p.parse_args()
    assemble(
        args.frames,
        args.out,
        hold_ms=args.hold_ms,
        fade_steps=args.fade_steps,
        max_width=args.max_width,
        colors=args.colors,
    )


if __name__ == "__main__":
    main()
