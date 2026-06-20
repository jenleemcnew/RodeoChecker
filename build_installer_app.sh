#!/bin/bash
# build_installer_app.sh — DEV TOOL. Run this to produce the release zip.
# Lives in the git repo but is NOT included in the distributable zip.
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
VERSION="$(cat "$REPO/VERSION")"
RELEASES_DIR="$(dirname "$REPO")/../RodeoChecker_Releases"
STAGING="$(mktemp -d)/RodeoChecker"
ZIP_NAME="RodeoChecker-v${VERSION}.zip"

echo "=== Building RodeoChecker release v${VERSION} ==="

mkdir -p "$STAGING"

# ── Copy distributable source files ──────────────────────────────────────────
for f in RodeoChecker.py engine.py run_setup.sh VERSION CHANGELOG.md README.md INSTALL.md bronc_icon.png; do
    [ -f "$REPO/$f" ] && cp "$REPO/$f" "$STAGING/"
done
[ -d "$REPO/reference_data" ] && cp -r "$REPO/reference_data" "$STAGING/"

# ── Build Install Update.app ─────────────────────────────────────────────────
APP="$STAGING/Install Update.app"
mkdir -p "$APP/Contents/MacOS"
mkdir -p "$APP/Contents/Resources"

cat > "$APP/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Install Update</string>
    <key>CFBundleDisplayName</key>
    <string>Install Update</string>
    <key>CFBundleIdentifier</key>
    <string>com.rodeochecker.installer</string>
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

cat > "$APP/Contents/MacOS/launch" << 'EOF'
#!/bin/bash
# Use BASH_SOURCE so the path resolves correctly when macOS launches the bundle
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SETUP="$DIR/run_setup.sh"

if [ ! -f "$SETUP" ]; then
    osascript -e 'display alert "Rodeo Checker — Install Update" message "Could not find run_setup.sh.\n\nMake sure Install Update.app is still inside the RodeoChecker folder you unzipped." as critical'
    exit 1
fi

# Safari quarantines every file in a downloaded zip. Clear it so the scripts can run.
xattr -cr "$DIR" 2>/dev/null || true

osascript -e 'display alert "Rodeo Checker — Install Update" message "This will install the latest version of Rodeo Checker.\n\nClick OK to continue." buttons {"Cancel", "OK"} default button "OK"' 2>/dev/null
if [ $? -ne 0 ]; then
    exit 0
fi

cd "$DIR"
bash "$SETUP" > /tmp/rodeochecker_install.log 2>&1
RESULT=$?

if [ $RESULT -eq 0 ]; then
    osascript -e 'display alert "Rodeo Checker — Install Update" message "Update installed!\n\nYou can now close this window and use the Rodeo Checker icon on your Desktop as usual." as informational'
else
    osascript -e 'display alert "Rodeo Checker — Install Update" message "Something went wrong during setup.\n\nA log was saved to /tmp/rodeochecker_install.log — send a screenshot of it if you need help." as critical'
fi
EOF

chmod +x "$APP/Contents/MacOS/launch"

# ── Create zip ────────────────────────────────────────────────────────────────
mkdir -p "$RELEASES_DIR"
STAGING_PARENT="$(dirname "$STAGING")"
cd "$STAGING_PARENT"
zip -r "$RELEASES_DIR/$ZIP_NAME" "RodeoChecker/" --exclude "*.DS_Store" --exclude "*__pycache__*" --exclude "*.pyc"

rm -rf "$STAGING_PARENT"

echo ""
echo "✓ Release zip: $RELEASES_DIR/$ZIP_NAME"
echo ""
echo "To replace the v${VERSION} GitHub release asset, run:"
echo "  gh release upload v${VERSION} \"$RELEASES_DIR/$ZIP_NAME\" --repo jenleemcnew/RodeoChecker --clobber"
