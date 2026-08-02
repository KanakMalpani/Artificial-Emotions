#!/usr/bin/env python3
"""Deterministic CLI → docs/media/avoidance.svg (GitHub-renderable).

Seeds a temp memory file with six encounters of ai-04 and zero selections,
runs ``emotions memory avoiding --path …`` via ``cli.main``, and wraps
stdout in a terminal SVG.
"""

from __future__ import annotations

import argparse
import html
import io
import os
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Editable / source-tree import
_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from artificial_emotions.avoidance import MIN_ENCOUNTERS_FOR_AVOIDANCE  # noqa: E402
from artificial_emotions.cli import main as cli_main  # noqa: E402
from artificial_emotions.memory import PersistentMemory  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "docs" / "media" / "avoidance.svg"


def seed_memory(path: Path) -> None:
    mem = PersistentMemory.load(path)
    for i in range(MIN_ENCOUNTERS_FOR_AVOIDANCE):
        mem.record_session(
            domain="ai",
            session_id=f"demo-s{i}",
            question_ids=["ai-04", "other"],
            best_question_id="other",
            primary_feeling="curiosity",
            steps_taken=3,
        )
    mem.save()


def run_avoiding(path: Path) -> str:
    os.environ.pop("CURIOSITY_NO_MEMORY", None)
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = cli_main(["memory", "avoiding", "--path", str(path)])
    if rc != 0:
        raise SystemExit(
            f"emotions memory avoiding failed ({rc}):\n{err.getvalue() or out.getvalue()}"
        )
    return out.getvalue().rstrip() + "\n"


def wrap_svg(stdout: str, prompt: str = "$ emotions memory avoiding") -> str:
    lines = [prompt, *stdout.rstrip("\n").split("\n")]
    wrapped: list[str] = []
    for line in lines:
        if len(line) <= 88:
            wrapped.append(line)
            continue
        words = line.split(" ")
        cur = ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if len(trial) > 88 and cur:
                wrapped.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            wrapped.append(cur)

    line_h = 18
    pad_x = 20
    width = 760
    height = 44 + line_h * len(wrapped) + 28
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="emotions memory avoiding CLI output">',
        "<title>emotions memory avoiding — pattern, not motive</title>",
        f'<rect width="{width}" height="{height}" rx="8" fill="#1a1b26"/>',
        '<circle cx="28" cy="18" r="5" fill="#ff5f56"/>',
        '<circle cx="48" cy="18" r="5" fill="#ffbd2e"/>',
        '<circle cx="68" cy="18" r="5" fill="#27c93f"/>',
    ]
    y0 = 44
    for i, line in enumerate(wrapped):
        y = y0 + i * line_h
        fill = "#7aa2f7" if i == 0 else "#c0caf5"
        parts.append(
            f'<text x="{pad_x}" y="{y}" font-family="ui-monospace, SFMono-Regular, '
            f'Menlo, Consolas, monospace" font-size="13" fill="{fill}">'
            f"{html.escape(line)}</text>"
        )
    parts.append("</svg>\n")
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    with tempfile.TemporaryDirectory(prefix="ae-avoidance-demo-") as tmp:
        mem_path = Path(tmp) / "memory.json"
        # Silence first-write privacy notice on stderr during seed
        err = io.StringIO()
        with redirect_stderr(err):
            seed_memory(mem_path)
        stdout = run_avoiding(mem_path)

    if "ai-04" not in stdout or "either good judgment or avoidance" not in stdout:
        raise SystemExit(f"unexpected avoiding output:\n{stdout}")

    svg = wrap_svg(stdout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(svg, encoding="utf-8")
    size = args.out.stat().st_size
    print(f"wrote {args.out} ({size} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
