#!/usr/bin/env bash
# Publish the packaged build to Itch.io as a free, unlisted/private project,
# using butler (https://itch.io/docs/butler/).  Run AFTER ./build.sh.
#
#     ITCH_TARGET="your-user/pac-man" ./itch_push.sh
#
# One-time setup:
#   1. Create the project on itch.io and set its visibility to "Restricted"
#      (unlisted/private) with a price of $0.
#   2. Install butler and run:  butler login
set -euo pipefail

APP="pac-man"
TARGET="${ITCH_TARGET:-your-itch-username/pac-man}"

case "$(uname -s)" in
    Linux*)  CHANNEL="linux" ;;
    Darwin*) CHANNEL="macos" ;;
    MINGW*|MSYS*|CYGWIN*) CHANNEL="windows" ;;
    *)       CHANNEL="unknown" ;;
esac

if ! command -v butler >/dev/null 2>&1; then
    echo "butler not found. Install it from https://itch.io/docs/butler/"
    exit 1
fi

echo ">> Pushing dist/${APP} to ${TARGET}:${CHANNEL}"
butler push "dist/${APP}" "${TARGET}:${CHANNEL}"
echo "Done. The build is live on the (unlisted) project page."
