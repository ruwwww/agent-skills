#!/usr/bin/env bash
# Installer script to restore and setup skills on remote instance from GitHub
set -euo pipefail

DEST_HOME="${1:-${HOME}}"

echo "=========================================================="
echo "  Setting up Agent Skills & Superpowers in ${DEST_HOME}"
echo "=========================================================="

mkdir -p "${DEST_HOME}/.agents/skills" "${DEST_HOME}/.hermes/skills" "${DEST_HOME}/.codex"

# 1. Install universal skills into ~/.agents/skills
if [ -d "agents-skills" ]; then
  echo "-> Installing Universal Skills (Superpowers, Codex, Claude Code)..."
  rsync -a agents-skills/ "${DEST_HOME}/.agents/skills/"
fi

# 2. Install Hermes domain skills into ~/.hermes/skills
if [ -d "hermes-skills" ]; then
  echo "-> Installing Hermes Domain Skills (MLOps, CUDA, DGPO, Papers)..."
  rsync -a hermes-skills/ "${DEST_HOME}/.hermes/skills/"
fi

# 3. Create symlinks for universal agent discovery
ln -sfn "${DEST_HOME}/.agents/skills" "${DEST_HOME}/.codex/skills" 2>/dev/null || true

echo "=========================================================="
echo "  Done! All skills installed successfully."
echo "=========================================================="
