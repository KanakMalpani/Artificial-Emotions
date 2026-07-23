"""Allow `python -m artificial_curiosity.mcp_server` via package module path.

Also supports: `python -m artificial_curiosity` → prints help pointing at MCP / CLI.
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "Artificial Curiosity\n"
        "  CLI:  curiosity spark | curiosity serve | curiosity run\n"
        "  MCP:  curiosity-mcp  OR  python -m artificial_curiosity.mcp_server\n"
        "  API:  curiosity serve → http://127.0.0.1:8000/docs\n",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
