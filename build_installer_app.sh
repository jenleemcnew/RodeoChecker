#!/bin/bash
# build_installer_app.sh — DEV TOOL. Run this to produce the release zip.
# Lives in the git repo but is NOT included in the distributable zip.
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
VERSION="$(cat "$REPO/VERSION")"
RELEASES_DIR="$(dirname "$REPO")/RodeoChecker_Releases"
STAGING="$(mktemp -d)/RodeoChecker"
ZIP_NAME="RodeoChecker-v${VERSION}.zip"

echo "=== Building RodeoChecker release v${VERSION} ==="

mkdir -p "$STAGING"

# ── Copy distributable source files ──────────────────────────────────────────
for f in RodeoChecker.py engine.py run_setup.sh VERSION CHANGELOG.md README.md INSTALL.md bronc_icon.png; do
    [ -f "$REPO/$f" ] && cp "$REPO/$f" "$STAGING/"
done
[ -d "$REPO/reference_data" ] && cp -r "$REPO/reference_data" "$STAGING/"

# ── Build Install Update.app via osacompile ───────────────────────────────────
# osacompile produces a real compiled AppleScript app.
# On macOS Sequoia this still requires Privacy & Security > Open Anyway once,
# but after that it runs cleanly with no Terminal needed.
#
# Path bug note: `path to me` returns a trailing slash, which makes `dirname`
# return the app path itself instead of the parent. Strip the slash first.

TMPSCRIPT="$(mktemp /tmp/rodeochecker_installer_XXXX.applescript)"

cat > "$TMPSCRIPT" << 'APPLESCRIPT'
on run
    -- Try to find the RodeoChecker folder automatically.
    -- macOS Sequoia may translocate the app to a temp path, so if the
    -- auto-detected path doesn't contain run_setup.sh, fall back to a
    -- folder picker so the user can point us to the right place.
    set appBundle to POSIX path of (path to me)
    set rcFolder to do shell script "p=" & quoted form of appBundle & "; dirname \"${p%/}\""
    set setupScript to rcFolder & "/run_setup.sh"

    -- Check if auto-detection worked; if not, ask the user to locate the folder
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

# Remove any stale shell script left over from previous app builds —
# osacompile may inherit files from an existing bundle at that path,
# and a foreign file invalidates the code signature (causes -47 / "damaged").
rm -f "$STAGING/Install Update.app/Contents/MacOS/launch"

# Re-sign with a fresh ad-hoc signature so the signature matches
# exactly what will be in the zip.
codesign --force --deep --sign - "$STAGING/Install Update.app"
codesign --verify --deep "$STAGING/Install Update.app" && echo "✓ Signature valid"

echo "✓ Built Install Update.app"

# ── Create zip (delete first so zip -r never retains stale entries) ──────────
mkdir -p "$RELEASES_DIR"
rm -f "$RELEASES_DIR/$ZIP_NAME"
STAGING_PARENT="$(dirname "$STAGING")"
cd "$STAGING_PARENT"
zip -r "$RELEASES_DIR/$ZIP_NAME" "RodeoChecker/" --exclude "*.DS_Store" --exclude "*__pycache__*" --exclude "*.pyc"

rm -rf "$STAGING_PARENT"

echo ""
echo "✓ Release zip: $RELEASES_DIR/$ZIP_NAME"
echo ""
echo "To replace the v${VERSION} GitHub release asset, run:"
echo "  gh release upload v${VERSION} \"$RELEASES_DIR/$ZIP_NAME\" --repo jenleemcnew/RodeoChecker --clobber"
