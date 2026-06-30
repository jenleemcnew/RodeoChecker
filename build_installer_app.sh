#!/bin/bash
# build_installer_app.sh — DEV TOOL. Run this to produce the release zip + pkg.
# Lives in the git repo but is NOT included in the distributable zip.
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
VERSION="$(cat "$REPO/VERSION")"
RELEASES_DIR="$(dirname "$REPO")/RodeoChecker_Releases"
STAGING="$(mktemp -d)/RodeoChecker"
ZIP_NAME="RodeoChecker-v${VERSION}.zip"
PKG_NAME="RodeoChecker-v${VERSION}.pkg"

echo "=== Building RodeoChecker release v${VERSION} ==="

mkdir -p "$STAGING"

# ── Copy distributable source files ──────────────────────────────────────────
for f in RodeoChecker.py engine.py run_setup.sh VERSION CHANGELOG.md README.md INSTALL.md bronc_icon.png; do
    [ -f "$REPO/$f" ] && cp "$REPO/$f" "$STAGING/"
done
[ -d "$REPO/reference_data" ] && cp -r "$REPO/reference_data" "$STAGING/"

# ── Build .pkg installer ──────────────────────────────────────────────────────
# The .pkg installs source files to ~/Library/Application Support/RodeoChecker/
# and runs run_setup.sh as a postinstall script.
# No Gatekeeper app-bundle issues — macOS Installer.app handles execution.
# Still requires Privacy & Security > Open Anyway once for unsigned .pkg.

PKGROOT="$(mktemp -d)"
PKGSCRIPTS="$(mktemp -d)"
INSTALL_SUBPATH="Library/Application Support/RodeoChecker"

# Payload: source files go into the package root at the install subpath
mkdir -p "$PKGROOT/$INSTALL_SUBPATH"
cp -r "$STAGING/." "$PKGROOT/$INSTALL_SUBPATH/"

# Bundle run_setup.sh into Scripts/ so it's available before payload is committed
cp "$REPO/run_setup.sh" "$PKGSCRIPTS/run_setup.sh"
chmod +x "$PKGSCRIPTS/run_setup.sh"

# Postinstall: call run_setup.sh from the Scripts dir (always present during execution)
cat > "$PKGSCRIPTS/postinstall" << 'EOF'
#!/bin/bash
TARGET_USER="$(stat -f '%Su' /dev/console 2>/dev/null || echo "$USER")"
INSTALL_DIR="/Users/$TARGET_USER/Library/Application Support/RodeoChecker"
SETUP="$(dirname "$0")/run_setup.sh"

# cd into the install dir so run_setup.sh can find RodeoChecker.py etc.
su "$TARGET_USER" -c "cd '$INSTALL_DIR' && bash '$SETUP'"
EOF
chmod +x "$PKGSCRIPTS/postinstall"

# Build the .pkg
mkdir -p "$RELEASES_DIR"
pkgbuild \
    --root "$PKGROOT" \
    --scripts "$PKGSCRIPTS" \
    --identifier "com.rodeochecker.installer" \
    --version "$VERSION" \
    --install-location "/" \
    "$RELEASES_DIR/$PKG_NAME"

rm -rf "$PKGROOT" "$PKGSCRIPTS"
echo "✓ Built $PKG_NAME"

# ── Build Install Update.app via osacompile (kept as zip fallback) ────────────
TMPSCRIPT="$(mktemp /tmp/rodeochecker_installer_XXXX.applescript)"

cat > "$TMPSCRIPT" << 'APPLESCRIPT'
on run
    set appBundle to POSIX path of (path to me)
    set rcFolder to do shell script "p=" & quoted form of appBundle & "; dirname \"${p%/}\""
    set setupScript to rcFolder & "/run_setup.sh"

    try
        do shell script "test -f " & quoted form of setupScript
    on error
        display alert "Rodeo Checker — Install Update" message "One more step: please select the RodeoChecker folder in the next window." as informational buttons {"OK"} default button "OK"
        set chosenFolder to choose folder with prompt "Select the RodeoChecker folder you unzipped (it contains run_setup.sh):"
        set rcFolder to POSIX path of chosenFolder
        if rcFolder ends with "/" then set rcFolder to text 1 thru -2 of rcFolder
        set setupScript to rcFolder & "/run_setup.sh"
        try
            do shell script "test -f " & quoted form of setupScript
        on error
            display alert "Rodeo Checker — Install Update" message "Could not find run_setup.sh in the selected folder." & return & return & "Please select the RodeoChecker folder that contains run_setup.sh." as critical
            return
        end try
    end try

    do shell script "xattr -cr " & quoted form of rcFolder

    set response to button returned of (display alert "Rodeo Checker — Install Update" message "This will install the latest version of Rodeo Checker." & return & return & "Click OK to continue." buttons {"Cancel", "OK"} default button "OK")
    if response is "Cancel" then return

    try
        do shell script "bash " & quoted form of setupScript & " > /tmp/rodeochecker_install.log 2>&1"
        display alert "Rodeo Checker — Install Update" message "Update installed!" & return & return & "You can now close this window and double-click the Rodeo Checker icon on your Desktop." as informational
    on error
        display alert "Rodeo Checker — Install Update" message "Something went wrong during setup." & return & return & "A log was saved to /tmp/rodeochecker_install.log — send a screenshot if you need help." as critical
    end try
end run
APPLESCRIPT

osacompile -o "$STAGING/Install Update.app" "$TMPSCRIPT"
rm "$TMPSCRIPT"
rm -f "$STAGING/Install Update.app/Contents/MacOS/launch"
codesign --force --deep --sign - "$STAGING/Install Update.app"
codesign --verify --deep "$STAGING/Install Update.app" && echo "✓ App signature valid"

# ── Create zip (delete first so zip -r never retains stale entries) ──────────
rm -f "$RELEASES_DIR/$ZIP_NAME"
STAGING_PARENT="$(dirname "$STAGING")"
cd "$STAGING_PARENT"
zip -r "$RELEASES_DIR/$ZIP_NAME" "RodeoChecker/" --exclude "*.DS_Store" --exclude "*__pycache__*" --exclude "*.pyc"

rm -rf "$STAGING_PARENT"

echo ""
echo "✓ Release zip: $RELEASES_DIR/$ZIP_NAME"
echo "✓ Release pkg: $RELEASES_DIR/$PKG_NAME"
echo ""
echo "Upload both to GitHub:"
echo "  gh release upload v${VERSION} \"$RELEASES_DIR/$PKG_NAME\" \"$RELEASES_DIR/$ZIP_NAME\" --repo jenleemcnew/RodeoChecker --clobber"
