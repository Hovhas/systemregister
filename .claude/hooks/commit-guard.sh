#!/bin/bash
# Commit Guard Hook
#
# Blockerar destruktiva git-operationer.
# Triggas: PreToolUse (matcher: Bash)

# Läs tool input från stdin
INPUT=$(cat)

# Extrahera kommandot
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

if [ -z "$COMMAND" ]; then
    exit 0
fi

# Normalisera: tabs → mellanslag, dubbla mellanslag → enkla, versaler → lowercase
NORM=$(echo "$COMMAND" | tr '\t' ' ' | tr -s ' ' | tr '[:upper:]' '[:lower:]')

# git reset --hard
if echo "$NORM" | grep -qE 'git reset --hard'; then
    echo "BLOCKERAD: git reset --hard är en destruktiv operation."
    exit 1
fi

# git push --force / -f — men tillåt --force-with-lease (säker operation)
if echo "$NORM" | grep -qE 'git push (--force|-f)\b'; then
    if ! echo "$NORM" | grep -qE 'git push --force-with-lease'; then
        echo "BLOCKERAD: git push --force är en destruktiv operation. Använd --force-with-lease om nödvändigt."
        exit 1
    fi
fi

# git clean -f
if echo "$NORM" | grep -qE 'git clean -f'; then
    echo "BLOCKERAD: git clean -f är en destruktiv operation."
    exit 1
fi

# git checkout -- . (bulk-återställning av worktree)
if echo "$NORM" | grep -qE 'git checkout -- \.'; then
    echo "BLOCKERAD: git checkout -- . är en destruktiv bulk-operation."
    exit 1
fi

# git restore . (bulk-återställning av worktree)
if echo "$NORM" | grep -qE 'git restore \.'; then
    echo "BLOCKERAD: git restore . är en destruktiv bulk-operation."
    exit 1
fi

# git rebase — varning men blockerar inte
if echo "$NORM" | grep -qE 'git rebase\b'; then
    echo "VARNING: git rebase kan vara destruktivt för pushade commits."
    exit 0
fi

exit 0
