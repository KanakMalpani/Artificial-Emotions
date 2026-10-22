#!/bin/bash
# Push backtest/prereg checkpoints. DISABLED BY DEFAULT: every push needs Kanak's own "Approved" in SWE's DM.
# Usage: PUSH_APPROVED=yes push_checkpoint.sh <full HEAD sha that Kanak approved>
set -euo pipefail
REPO=${REPO:-/workspace/Artificial-Emotions}
echo "Each push needs Kanak's DM approval (fast-forward only, never main, never force)."
[ "${PUSH_APPROVED:-}" = yes ] || { echo "REFUSE: PUSH_APPROVED!=yes"; exit 1; }
[ "$(git -C "$REPO" rev-parse --abbrev-ref HEAD)" = backtest/prereg ] || { echo "REFUSE: branch"; exit 1; }
[ "${1:-}" = "$(git -C "$REPO" rev-parse HEAD)" ] || { echo "REFUSE: arg must equal HEAD $(git -C "$REPO" rev-parse HEAD)"; exit 1; }
git -C "$REPO" push origin backtest/prereg:backtest/prereg
