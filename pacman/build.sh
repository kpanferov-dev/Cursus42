#!/usr/bin/env bash
# Build a self-contained Pac-Man release with PyInstaller and zip it for
# upload to a public platform (Itch.io / Steam).  Run from the repo root:
#
#     ./build.sh
#
# Output:
#   dist/pac-man/              one-folder application (run ./pac-man inside)
#   dist/pac-man-<os>.zip      ready to drag-and-drop onto Itch.io
#
# The packaged build is fully functional and needs no Python install on the
# player's machine.  It bundles config.json + INSTRUCTIONS.txt + itch.toml.
set -euo pipefail

PYBIN="${PYBIN:-python3}"
APP="pac-man"

echo ">> Installing build dependencies (pygame, mazegenerator wheel, pyinstaller)"
"$PYBIN" -m pip install --upgrade pip
"$PYBIN" -m pip install pygame pyinstaller
# Use the assigned A-Maze-ing wheel exactly as provided, never a rewrite.
if ls ./mazegenerator-*.whl >/dev/null 2>&1; then
    "$PYBIN" -m pip install ./mazegenerator-*.whl
else
    echo "!! mazegenerator-*.whl not found at repo root."
    echo "   Drop the assigned A-Maze-ing wheel here before packaging."
    exit 1
fi

echo ">> Cleaning previous build"
rm -rf build dist

echo ">> Running PyInstaller"
"$PYBIN" -m PyInstaller --noconfirm --clean pacman.spec

# Determine an OS tag for the archive name.
case "$(uname -s)" in
    Linux*)  OS_TAG="linux" ;;
    Darwin*) OS_TAG="macos" ;;
    MINGW*|MSYS*|CYGWIN*) OS_TAG="windows" ;;
    *)       OS_TAG="unknown" ;;
esac

echo ">> Zipping dist/${APP} -> dist/${APP}-${OS_TAG}.zip"
( cd dist && zip -r -q "${APP}-${OS_TAG}.zip" "${APP}" )

echo ""
echo "Done. Test it with:   ./dist/${APP}/${APP}"
echo "Upload dist/${APP}-${OS_TAG}.zip to Itch.io (or run ./itch_push.sh)."
