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

# ── Create "Install Update.command" ──────────────────────────────────────────
# .app bundles are blocked by macOS Sequoia Gatekeeper (error -47) when
# downloaded from the internet. A .command file opens in Terminal with a
# simple "are you sure?" prompt — no Privacy & Security dance needed.

cat > "$STAGING/Install Update.command" << 'EOF'
#!/bin/bash
clear
DIR="$(cd "$(dirname "$0")" && pwd)"
SETUP="$DIR/run_setup.sh"

echo "============================================="
echo "   Rodeo Checker — Install / Update"
echo "============================================="
echo ""

if [ ! -f "$SETUP" ]; then
    echo "ERROR: Could not find run_setup.sh."
    echo "Make sure this file is still inside the RodeoChecker folder you unzipped."
    echo ""
    echo "Press any key to close…"
    read -n1
    exit 1
fi

# Clear Safari quarantine from the whole folder
xattr -cr "$DIR" 2>/dev/null || true

echo "This will install/update Rodeo Checker on your Desktop."
echo ""
read -p "Press ENTER to continue (or close this window to cancel)… "
echo ""

bash "$SETUP" 2>&1 | tee /tmp/rodeochecker_install.log
RESULT=${PIPESTATUS[0]}

echo ""
if [ $RESULT -eq 0 ]; then
    echo "============================================="
    echo "   Done! You can close this window."
    echo "   Use the Rodeo Checker icon on your Desktop."
    echo "============================================="
else
    echo "============================================="
    echo "   Something went wrong."
    echo "   Log saved to /tmp/rodeochecker_install.log"
    echo "   Send a screenshot of this window if you"
    echo "   need help."
    echo "============================================="
fi
echo ""
echo "Press any key to close…"
read -n1
EOF

chmod +x "$STAGING/Install Update.command"

echo "✓ Created Install Update.command"

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
