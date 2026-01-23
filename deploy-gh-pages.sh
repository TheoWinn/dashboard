#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/conda/envs/default/bin:$PATH"

# --- config (adjust) ---
REPO_DIR="/home/mlci_2025s1_group1/Dashboard/deploy-worktree"
BUILD_BRANCH="ara/hostinfra"
WORKTREE_DIR="/tmp/gh-pages"
DIST_DIR="frontend/dist"
FRONTEND_DIR="frontend"
NPM="/opt/conda/envs/default/bin/npm"

cd "$REPO_DIR"

# Ensure we have latest
git fetch origin --prune

# Delete any local changes
git checkout "$BUILD_BRANCH" 2>/dev/null || git checkout -b "$BUILD_BRANCH" "origin/$BUILD_BRANCH"
git reset --hard "origin/$BUILD_BRANCH"
git clean -fd
rm -rf "$DIST_DIR"

# Build
"$NPM" --prefix "$FRONTEND_DIR" ci
"$NPM" --prefix "$FRONTEND_DIR" run build

# Worktree setup
git worktree prune
git show-ref --verify --quiet refs/heads/gh-pages || git branch gh-pages origin/gh-pages
rm -rf "$WORKTREE_DIR"
git worktree add "$WORKTREE_DIR" gh-pages

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
