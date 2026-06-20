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

# ── Build Install Update.app via osacompile (proper AppleScript bundle) ───────
# Shell-script-as-CFBundleExecutable is blocked by macOS Sequoia (-47 error).
# osacompile produces a real compiled app that Gatekeeper/Finder accept.

TMPSCRIPT="$(mktemp /tmp/rodeochecker_installer_XXXX.applescript)"

cat > "$TMPSCRIPT" << 'APPLESCRIPT'
on run
    -- Locate the RodeoChecker folder (parent of this .app bundle)
    set myPath to POSIX path of (path to me)
    set rcFolder to do shell script "dirname " & quoted form of myPath
    set setupScript to rcFolder & "/run_setup.sh"

    -- Verify run_setup.sh exists
    try
        do shell script "test -f " & quoted form of setupScript
    on error
        display alert "Rodeo Checker — Install Update" message "Could not find run_setup.sh." & return & return & "Make sure Install Update.app is still inside the RodeoChecker folder you unzipped." as critical
        return
    end try

    -- Clear Safari quarantine from the whole folder so scripts can run
    do shell script "xattr -cr " & quoted form of rcFolder

    -- Confirm before running
    set response to button returned of (display alert "Rodeo Checker — Install Update" message "This will install the latest version of Rodeo Checker." & return & return & "Click OK to continue." buttons {"Cancel", "OK"} default button "OK")
    if response is "Cancel" then return

    -- Run setup
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

echo "✓ Built Install Update.app"

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
