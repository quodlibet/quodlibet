#!/bin/bash
# Run Quod Libet from source with a proper macOS bundle identity, so that
# MPRemoteCommandCenter and media key routing work during development.
#
# Usage: ./dev-utils/macos/run.sh [quodlibet args...]
#
# How it works: NSBundle.mainBundle() uses the executable's path on disk to
# find Info.plist. By hard-linking the venv Python binary into the stub .app
# and exec'ing that link, the Python process appears to live inside the bundle,
# so macOS assigns it the bundle ID from Info.plist and rcd routes media keys
# to it.

set -e

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$(dirname "$0")/QuodLibetDev.app"
PYTHON_SRC="$REPO/.venv/bin/python"
LAUNCHER="$APP/Contents/MacOS/quodlibet-dev"

if [ ! -f "$PYTHON_SRC" ]; then
    echo "error: no venv found at $PYTHON_SRC — run 'poetry install' first" >&2
    exit 1
fi

# Copy the venv Python into the .app so _NSGetExecutablePath returns a path
# inside the bundle. Symlinks don't work (macOS resolves them). Hard links
# don't work across filesystems, so we copy and skip if already up to date.
if [ ! -f "$LAUNCHER" ] || [ "$PYTHON_SRC" -nt "$LAUNCHER" ]; then
    cp -f "$PYTHON_SRC" "$LAUNCHER"
fi

PYTHON_VERSION=$("$PYTHON_SRC" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
export PYTHONPATH="$REPO/.venv/lib/python${PYTHON_VERSION}/site-packages${PYTHONPATH:+:$PYTHONPATH}"

exec "$LAUNCHER" "$REPO/quodlibet.py" "$@"
