#!/bin/bash

# LandRight Git Hooks Installer
# Sets up pre-push hook for quality gate enforcement
#
# Usage: ./scripts/install-githooks.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.githooks"

echo "============================================"
echo "  Installing LandRight Git Hooks"
echo "============================================"
echo ""

# Check if hooks directory exists
if [ ! -d "$HOOKS_DIR" ]; then
    echo "ERROR: .githooks directory not found"
    exit 1
fi

# Make hooks executable
chmod +x "$HOOKS_DIR"/*

# Configure git to use custom hooks directory
git config core.hooksPath .githooks

echo "✅ Git hooks installed successfully!"
echo ""
echo "Hooks path set to: .githooks"
echo ""
echo "Installed hooks:"
for hook in "$HOOKS_DIR"/*; do
    if [ -f "$hook" ]; then
        echo "  - $(basename "$hook")"
    fi
done
echo ""
echo "============================================"
echo ""
echo "The pre-push hook will now run Playwright"
echo "smoke tests before each push."
echo ""
echo "To bypass (emergency only):"
echo "  git push --no-verify"
echo ""
echo "To uninstall:"
echo "  git config --unset core.hooksPath"
echo ""
