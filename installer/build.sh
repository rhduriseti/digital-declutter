#!/bin/bash
# Build the Claire Mac installer (.dmg).
# Run from the repo root: bash installer/build.sh
# Requirements: venv activated, node_modules installed in frontend/

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Step 1: Building Python API binary with PyInstaller ==="
source venv/bin/activate
pip install pyinstaller --quiet
pyinstaller installer/build_api.spec --distpath installer/dist --noconfirm
echo "Binary built: installer/dist/declutter-api-bin"

echo ""
echo "=== Step 2: Building Electron app + DMG ==="
cd frontend
npm run electron:build

echo ""
echo "=== Done! ==="
echo "Installer: $(ls "$REPO_ROOT/frontend/dist-electron/"*.dmg 2>/dev/null || echo 'check frontend/dist-electron/')"
