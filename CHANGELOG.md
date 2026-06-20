# Changelog

All notable changes to Rodeo Checker are listed here. Versions match the
tag on each GitHub Release — check the `VERSION` file in your local copy
against this list to see if you're current.

## 1.1.0

- **Fixed: TeamRoping heeler names were being skipped.** The header (first
  rider) was always checked against the card and suspended lists, but the
  heeler (second rider, listed in extra columns on the alpha sheet) was
  not. This version checks both riders.
- Added a version number to the app window title and header, so you can
  tell at a glance which version you're running.

## 1.0.0

- Initial release: alpha sheet vs. card numbers vs. suspended list
  matching, 4-sheet Excel report, dark-themed desktop GUI, one-time Mac
  setup script.
