# 🏟 Rodeo Checker — Contestant Fines & Card Verification

Automated weekly tool that cross-references the rodeo entry list against the UPRA card numbers and suspended list, then generates a polished Excel report with all matches, fines owed, and totals.

---

## 📁 Repository Structure

```
RodeoChecker/
├── .github/
│   └── workflows/
│       └── weekly_report.yml   ← GitHub Actions: run manually, no fixed schedule
├── reference_data/
│   ├── card_numbers.xlsx       ← UPRA member card list (update occasionally)
│   └── suspended_list.xlsx     ← UPRA suspended list (update occasionally)
├── watched_folder/
│   └── (drop weekly alpha sheet here)
├── reports/
│   └── (generated reports saved here)
├── engine.py                   ← Matching + Excel report logic
├── RodeoChecker.py             ← Desktop GUI app (Mac/Windows)
├── run_setup.sh                ← One-time Mac setup script
└── README.md
```

---

## ⚡ Two Ways to Run

### Option A — Desktop App (weekly manual use)

Best for running the report yourself with a GUI.

1. **Clone or download** this repo
2. **Run setup once:**
   ```bash
   bash run_setup.sh
   ```
   This installs dependencies and creates a **Rodeo Checker** app on your Desktop.
3. **Every week:**
   - Drop the new alpha sheet into `watched_folder/`
   - Double-click **Rodeo Checker** on your Desktop
   - Click **⚡ RUN REPORT**
   - The Excel report opens automatically

### Option B — GitHub Actions (run on demand)

The workflow in `.github/workflows/weekly_report.yml` runs **whenever you trigger it** — no fixed schedule.

**Setup (one time):**
1. Push this repo to GitHub
2. Make sure the two reference files are committed in `reference_data/`

**Each time you need a report:**
1. Commit the new alpha sheet to `watched_folder/`
2. Go to **Actions → Weekly Rodeo Report → Run workflow → Run workflow**
3. The report is saved to `reports/` and appears as a downloadable **Artifact**

---

## 📊 Report Contents

The generated `Fines_Card_Verification_YYYY-MM-DD.xlsx` has four sheets:

| Sheet | Contents |
|-------|----------|
| ⚑ Summary | Stat boxes (entrants, flagged, suspended, with/without card, total $) + full flagged table |
| ✅ Entries With Cards | Every alpha-sheet name that matched a card number, A–Z |
| ❌ Entries Without Cards | Every alpha-sheet name with no card number match, A–Z |
| 💰 Fine Totals | Fines only — one row per offense, subtotal per person, grand total |

### Color Coding
- 🔴 **Red rows** — Person matched on the Suspended List (fines owed)
- 🔵 **Blue rows** — Person matched on Card Numbers list only, not suspended
- ⚪ **Grey rows** — No card match, not suspended
- 🟦 **Navy bars** — Subtotal per person / Grand total row
- 🟢 **Green cell** — Dollar total

### Team Roping (Header + Heeler)
Each TeamRoping entry on the alpha sheet lists two contestants — the header
(Rider Last/First Name) and the heeler (the extra name columns after Entry
Time). Both are checked independently against the card numbers and suspended
lists, and each appears in the report labeled `TeamRoping (Header)` /
`TeamRoping (Heeler)` so they're never missed.

---

## 🔄 Updating Reference Files

The card numbers and suspended list only change occasionally.

**Via Desktop App:** Click the **Update…** button next to the file in the app.

**Via GitHub:** Replace the file in `reference_data/` and commit/push.

---

## ⬆️ Updating to a New Version

To pick up engine fixes/features on an existing local copy:

```bash
git pull --rebase
```

If you're running the **Desktop App** copy (not a git clone), just replace
`engine.py` with the latest version from this repo and re-launch the app —
no need to re-run `run_setup.sh` unless the Desktop shortcut itself is broken.

---

## 🛠 Requirements

- Python 3.10+
- `pandas`
- `openpyxl`

Install manually:
```bash
pip install pandas openpyxl
```

---

## 🔒 Privacy Note

This repo is public. The contestant names, card numbers, and fine data it
handles are already publicly available UPRA information, so no privacy
restriction is needed here.
