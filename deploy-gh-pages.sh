#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/conda/envs/default/bin:$PATH"

# --- config (adjust) ---
REPO_DIR="/home/mlci_2025s1_group1/Dashboard/deploy-worktree"
BUILD_BRANCH="ara/hostinfra"
WORKTREE_DIR="/tmp/gh-pages"
DIST_DIR="frontend/dist"
FRONTEND_DIR="frontend"

cd "$REPO_DIR"

# Ensure we have latest
git fetch origin --prune

# Checkout the build branch and update it
git checkout "$BUILD_BRANCH"
git pull --ff-only origin "$BUILD_BRANCH"

# Load env vars for the build if you use a local .env
# If your build tooling reads frontend/.env automatically, you can skip exporting.
if [[ -f "$FRONTEND_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$FRONTEND_DIR/.env"
  set +a
fi

# Install + build
/opt/conda/envs/default/bin/npm --prefix "$FRONTEND_DIR" ci
/opt/conda/envs/default/bin/npm --prefix "$FRONTEND_DIR" run build

# Create or reuse gh-pages worktree
rm -rf "$WORKTREE_DIR"
git worktree add "$WORKTREE_DIR" gh-pages 2>/dev/null || git worktree add "$WORKTREE_DIR" -b gh-pages

# Clean gh-pages (keep only .git)
find "$WORKTREE_DIR" -mindepth 1 -maxdepth 1 ! -name ".git" -exec rm -rf {} +

# Copy dist contents
cp -R "$DIST_DIR"/. "$WORKTREE_DIR"/
touch "$WORKTREE_DIR/.nojekyll"

# Commit + push
cd "$WORKTREE_DIR"
git add -A
git commit -m "Deploy from $BUILD_BRANCH ($(date -u +'%Y-%m-%dT%H:%M:%SZ'))" || echo "No changes to commit"
git push origin gh-pages

# Cleanup
cd "$REPO_DIR"
git worktree remove "$WORKTREE_DIR" || true
