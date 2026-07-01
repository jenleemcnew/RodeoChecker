#!/bin/bash
# run_setup.sh  –  Run after downloading/unzipping a Rodeo Checker release.
# Safe to re-run any time there's an update: it reinstalls dependencies
# and rebuilds the Desktop launcher, replacing whatever was there before.

set -e
# When called from the pkg postinstall, $1 is the install path.
# When run directly, fall back to the script's own directory.
DIR="${1:-$(cd "$(dirname "$0")" && pwd)}"

VERSION="unknown"
if [ -f "$DIR/VERSION" ]; then
    VERSION="$(cat "$DIR/VERSION")"
fi

echo "=== Rodeo Checker Setup — version $VERSION ==="
echo ""

# ── 1. Find Python ────────────────────────────────────────────────────────────
echo "→ Locating Python 3…"

PYTHON=""
for candidate in \
    /opt/anaconda3/bin/python3 \
    /usr/local/anaconda3/bin/python3 \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    "$(which python3 2>/dev/null)"; do
    if [ -x "$candidate" ]; then
        version=$("$candidate" -c "import sys; print(sys.version_info >= (3,10))" 2>/dev/null)
        if [ "$version" = "True" ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    osascript -e 'display alert "Rodeo Checker Setup" message "Python 3.10 or newer is required but was not found.\n\nPlease download and install Python 3 from python.org, then run run_setup.sh again." as critical'
    echo "✗ Python 3.10+ not found. Please install from python.org and re-run."
    exit 1
fi

echo "✓ Found Python: $PYTHON"

# ── 2. Install Python dependencies ───────────────────────────────────────────
echo "→ Installing Python dependencies (pandas, openpyxl)…"
"$PYTHON" -m pip install pandas openpyxl --quiet --break-system-packages 2>/dev/null || \
"$PYTHON" -m pip install pandas openpyxl --quiet
echo "✓ Dependencies installed"

# ── 3. Create the Desktop launcher app ───────────────────────────────────────
echo "→ Creating Desktop launcher app…"

APP_PATH="$HOME/Desktop/Rodeo Checker.app"

rm -rf "$APP_PATH"

# macOS Sequoia blocks shell scripts as CFBundleExecutable (-47 "damaged" error).
# Use osacompile to produce a proper compiled AppleScript app bundle instead.
TMPSCRIPT="$(mktemp -t rodeochecker_launcher).applescript"
# Embed python and script paths as literal strings inside the AppleScript.
# Single-quote them in the shell command so spaces in paths are handled.
cat > "$TMPSCRIPT" << EOF
on run
    try
        do shell script "'${PYTHON}' '${DIR}/RodeoChecker.py'"
    on error errMsg
        display alert "Rodeo Checker" message "Could not launch: " & errMsg as critical
    end try
end run
EOF

osacompile -o "$APP_PATH" "$TMPSCRIPT"
rm "$TMPSCRIPT"
# Remove stale shell script left by osacompile so the signature is clean
rm -f "$APP_PATH/Contents/MacOS/launch"
codesign --force --deep --sign - "$APP_PATH"
xattr -cr "$APP_PATH" 2>/dev/null || true

echo "✓ Desktop app created: 'Rodeo Checker' on your Desktop"

# ── 4. Register with Gatekeeper ───────────────────────────────────────────────
spctl --add "$APP_PATH" 2>/dev/null || true

# ── 5. Done ───────────────────────────────────────────────────────────────────
echo ""
echo "==================================================="
echo " Setup complete! (version $VERSION)"
echo " Double-click 'Rodeo Checker' on your Desktop"
echo " to launch the app — no Terminal needed!"
echo ""
echo " Updating later? Download the newest version from"
echo " the GitHub Releases page, then double-click"
echo " 'Install Update' inside the unzipped folder —"
echo " no Terminal needed for that either."
echo "==================================================="
echo ""

# Only launch the app immediately when run interactively (not from pkg postinstall,
# where the payload isn't committed yet and the app would open to missing files).
if [ -z "$1" ]; then
    open "$APP_PATH"
fi
