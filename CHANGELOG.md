# Changelog

All notable changes to Rodeo Checker are listed here. Versions match the
tag on each GitHub Release — check the `VERSION` file in your local copy
against this list to see if you're current.

## 1.1.0

- **Fixed: TeamRoping heeler names were being skipped.** The header (first
  rider) was always checked against the card and suspended lists, but the
  heeler (second rider, listed in extra columns on the alpha sheet) was
  not. This version checks both riders. In testing against a real alpha
  sheet, this surfaced 32 heeler names that were previously invisible to
  the report, including real compliance hits that had been missed.
- Added a version number to the app window title and header, so you can
  tell at a glance which version you're running.
- Widened the "Total $ Owed" column on the Summary sheet so larger dollar
  amounts don't get cut off.

## 1.0.0

- Initial release: alpha sheet vs. card numbers vs. suspended list
  matching, 4-sheet Excel report (Summary, Entries With Cards, Entries
  Without Cards, Fine Totals), dark-themed desktop GUI, one-time Mac
  setup script.
