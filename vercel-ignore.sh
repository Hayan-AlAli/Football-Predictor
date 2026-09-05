#!/bin/bash
# Vercel ignoreCommand: exit 0 = skip build, exit 1 = build.
# Skips noisy redeploys for docs-only / test-only / meta-only changes.
set -u

PREV="${VERCEL_GIT_PREVIOUS_SHA:-}"
if [ -z "$PREV" ]; then
  # First deploy or no history available -> always build
  exit 1
fi

CHANGED=$(git diff --name-only "$PREV" HEAD 2>/dev/null || echo "__FULL_BUILD__")
if [ -z "$CHANGED" ] || [ "$CHANGED" = "__FULL_BUILD__" ]; then
  exit 1
fi

# Paths that never affect runtime behaviour
IGNORE_RE='(^docs/|^\.impeccable/|^\.superpowers/|^\.worktrees/|^\.vercel/|^\.github/|\.md$|^tests/|^\.gitignore$|^frontend/\.gitignore$|^LICENSE$|generate_results\.py$)'

if echo "$CHANGED" | grep -qvE "$IGNORE_RE"; then
  # At least one runtime-relevant file changed -> build
  exit 1
else
  echo "Skipping Vercel build: only docs/tests/meta changed:"
  echo "$CHANGED"
  exit 0
fi
