#!/bin/bash
# run_setup.sh  –  Run once after cloning/unzipping on Mac
# Automatically installs dependencies and creates a Desktop launcher app.

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Rodeo Checker Setup ==="
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

mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

cat > "$APP_PATH/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Rodeo Checker</string>
    <key>CFBundleDisplayName</key>
    <string>Rodeo Checker</string>
    <key>CFBundleIdentifier</key>
    <string>com.rodeochecker.app</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>launch</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

cat > "$APP_PATH/Contents/MacOS/launch" << 'ENDOFSCRIPT'
#!/bin/bash
ENDOFSCRIPT

cat >> "$APP_PATH/Contents/MacOS/launch" << EOF
SCRIPT="${DIR}/RodeoChecker.py"
PYTHON="${PYTHON}"
EOF

cat >> "$APP_PATH/Contents/MacOS/launch" << 'ENDOFSCRIPT'
if [ ! -f "$SCRIPT" ]; then
    osascript -e 'display alert "Rodeo Checker" message "Could not find RodeoChecker.py.\n\nMake sure you have not moved the RodeoChecker folder." as critical'
    exit 1
fi
cd "$(dirname "$SCRIPT")"
"$PYTHON" "$SCRIPT"
ENDOFSCRIPT

chmod +x "$APP_PATH/Contents/MacOS/launch"
xattr -cr "$APP_PATH" 2>/dev/null || true

echo "✓ Desktop app created: 'Rodeo Checker' on your Desktop"

# ── 4. Register with Gatekeeper ───────────────────────────────────────────────
spctl --add "$APP_PATH" 2>/dev/null || true

# ── 5. Done ───────────────────────────────────────────────────────────────────
echo ""
echo "==================================================="
echo " Setup complete!"
echo " Double-click 'Rodeo Checker' on your Desktop"
echo " to launch the app — no Terminal needed!"
echo "==================================================="
echo ""

open "$DIR"
sleep 1
open "$APP_PATH"
