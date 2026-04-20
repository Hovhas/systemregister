#!/bin/bash
# Auto-checkpoint hook - skapar automatisk backup innan riskfyllda operationer
# Triggas: PreToolUse för Edit/Write
#
# Debounce: max 1 checkpoint per 60 sekunder för att undvika overhead.
# Exkluderar __pycache__, node_modules från untracked.

set -e

MAX_CHECKPOINTS=20
CHECKPOINT_PREFIX="checkpoint-claude"
DEBOUNCE_SECONDS=60
DEBOUNCE_FILE="/tmp/.claude-checkpoint-last"

# Kontrollera att vi är i ett git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    exit 0
fi

# Debounce
if [ -f "$DEBOUNCE_FILE" ]; then
    LAST_TS=$(cat "$DEBOUNCE_FILE" 2>/dev/null || echo "0")
    NOW_TS=$(date +%s)
    DIFF=$((NOW_TS - LAST_TS))
    if [ "$DIFF" -lt "$DEBOUNCE_SECONDS" ]; then
        exit 0
    fi
fi

# Hoppa över om inga ändringar
if ! git status --porcelain | grep -q .; then
    exit 0
fi

date +%s > "$DEBOUNCE_FILE"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
STASH_MSG="${CHECKPOINT_PREFIX}-${TIMESTAMP}"

git stash push -m "$STASH_MSG" --include-untracked --quiet \
    -- ':!**/__pycache__/**' ':!**/node_modules/**' ':!**/.pytest_cache/**' ':!**/*.pyc' \
    2>/dev/null || true

if git stash list | grep -q "$STASH_MSG"; then
    git stash pop --quiet 2>/dev/null || true
    echo "[checkpoint] sparad" >&2
fi

# Rensa gamla checkpoints (behåll MAX_CHECKPOINTS)
CHECKPOINT_COUNT=$(git stash list | grep -c "$CHECKPOINT_PREFIX" 2>/dev/null || true)
CHECKPOINT_COUNT=${CHECKPOINT_COUNT:-0}

if [ "$CHECKPOINT_COUNT" -gt "$MAX_CHECKPOINTS" ]; then
    REMOVE_COUNT=$((CHECKPOINT_COUNT - MAX_CHECKPOINTS))
    git stash list | grep "$CHECKPOINT_PREFIX" | tail -n "$REMOVE_COUNT" | while read -r line; do
        STASH_INDEX=$(echo "$line" | grep -o 'stash@{[0-9]*}')
        git stash drop "$STASH_INDEX" --quiet 2>/dev/null || true
    done
fi

exit 0
