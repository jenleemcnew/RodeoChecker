#!/usr/bin/env python3
"""
RodeoChecker.py  –  Desktop GUI for the Fines & Card Verification report
Run:  python3 RodeoChecker.py
"""

import os
import sys
import glob
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import date
from pathlib import Path

# ── Paths relative to this script ────────────────────────────────────────────
BASE        = Path(__file__).parent.resolve()
WATCHED     = BASE / "watched_folder"
REF_DATA    = BASE / "reference_data"
REPORTS_DIR = BASE / "reports"
CARD_FILE   = REF_DATA / "card_numbers.xlsx"
SUSP_FILE   = REF_DATA / "suspended_list.xlsx"

for d in (WATCHED, REF_DATA, REPORTS_DIR):
    d.mkdir(exist_ok=True)

# ── Colour palette ────────────────────────────────────────────────────────────
BG       = "#0F1923"   # near-black background
CARD     = "#1A2535"   # card/panel bg
ACCENT   = "#C8960C"   # gold accent
ACCENT2  = "#E8B84B"   # lighter gold
RED      = "#DC2626"
GREEN    = "#22C55E"
TEXT     = "#F0EDE8"   # warm white
MUTED    = "#8899AA"
BORDER   = "#2A3A4A"

FONT_H   = ("Georgia", 22, "bold")
FONT_SUB = ("Georgia", 13)
FONT_B   = ("Calibri", 11, "bold")
FONT_N   = ("Calibri", 11)
FONT_S   = ("Calibri", 10)
FONT_M   = ("Courier New", 9)


def find_alpha_sheet() -> Path | None:
    """Find the most recently modified CSV or XLSX in the watched folder."""
    files = sorted(
        list(WATCHED.glob("*.csv")) + list(WATCHED.glob("*.xlsx")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


def open_file(path: str):
    """Open a file with the system default app."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        messagebox.showerror("Open Error", str(e))


def open_folder(path: str):
    """Reveal a folder in Finder / Explorer."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass


# ── Main Application ──────────────────────────────────────────────────────────

class RodeoCheckerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Fines & Card Verification  ·  Weekly Report Generator")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.geometry("780x680")
        self.minsize(680, 560)

        self._last_report = None
        self._build_ui()
        self._refresh_status()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header bar ───────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=CARD, height=80)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="🏟", font=("Segoe UI Emoji", 28),
                 bg=CARD, fg=ACCENT).pack(side="left", padx=(20, 6), pady=10)

        titl = tk.Frame(hdr, bg=CARD)
        titl.pack(side="left", pady=10)
        tk.Label(titl, text="FINES & CARD VERIFICATION", font=FONT_H,
                 bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(titl, text="Weekly Report Generator",
                 font=FONT_SUB, bg=CARD, fg=MUTED).pack(anchor="w")

        tk.Label(hdr, text=date.today().strftime("%B %d, %Y"),
                 font=FONT_N, bg=CARD, fg=MUTED).pack(side="right", padx=20)

        # Separator
        tk.Frame(self, bg=ACCENT, height=2).pack(fill="x")

        # ── Main content area ─────────────────────────────────────────────────
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=24, pady=16)

        # ── Step 1: Alpha Sheet ──────────────────────────────────────────────
        self._section(main, "STEP 1 — WEEKLY ENTRY LIST (ALPHA SHEET)")

        s1 = tk.Frame(main, bg=CARD, bd=0, relief="flat",
                      highlightbackground=BORDER, highlightthickness=1)
        s1.pack(fill="x", pady=(0, 12))

        row1 = tk.Frame(s1, bg=CARD)
        row1.pack(fill="x", padx=16, pady=12)

        tk.Label(row1, text="Drop file into watched folder OR browse:",
                 font=FONT_N, bg=CARD, fg=MUTED).pack(side="left")

        tk.Button(row1, text="📂  Browse…", font=FONT_B,
                  bg=ACCENT, fg="#0F1923", activebackground=ACCENT2,
                  relief="flat", padx=12, pady=4, cursor="hand2",
                  command=self._browse_alpha).pack(side="right", padx=(8, 0))
        tk.Button(row1, text="📁  Open Folder", font=FONT_S,
                  bg=CARD, fg=MUTED, activebackground=BORDER,
                  relief="flat", padx=10, pady=4, cursor="hand2",
                  command=lambda: open_folder(WATCHED)).pack(side="right")

        self._alpha_var = tk.StringVar(value="No file detected yet")
        self._alpha_lbl = tk.Label(s1, textvariable=self._alpha_var,
                                   font=FONT_M, bg=CARD, fg=GREEN,
                                   anchor="w", wraplength=680)
        self._alpha_lbl.pack(fill="x", padx=16, pady=(0, 10))

        # ── Step 2: Reference files ──────────────────────────────────────────
        self._section(main, "STEP 2 — REFERENCE FILES (auto-loaded)")

        s2 = tk.Frame(main, bg=CARD, bd=0, relief="flat",
                      highlightbackground=BORDER, highlightthickness=1)
        s2.pack(fill="x", pady=(0, 12))

        grid = tk.Frame(s2, bg=CARD)
        grid.pack(fill="x", padx=16, pady=12)

        for i, (label, path_attr, file_path) in enumerate([
            ("Card Numbers:", "_card_var", CARD_FILE),
            ("Suspended List:", "_susp_var", SUSP_FILE),
        ]):
            tk.Label(grid, text=label, font=FONT_B, bg=CARD,
                     fg=MUTED, width=18, anchor="w").grid(row=i, column=0, pady=3)
            var = tk.StringVar()
            setattr(self, path_attr, var)
            lbl = tk.Label(grid, textvariable=var, font=FONT_M,
                           bg=CARD, anchor="w")
            lbl.grid(row=i, column=1, sticky="w", padx=8)
            setattr(self, f"_ref_lbl_{i}", lbl)

            def _browse_ref(p=path_attr, fp=file_path):
                chosen = filedialog.askopenfilename(
                    title="Select file",
                    filetypes=[("Excel/CSV", "*.xlsx *.xls *.csv"), ("All", "*.*")]
                )
                if chosen:
                    import shutil
                    dest = REF_DATA / Path(chosen).name
                    shutil.copy2(chosen, dest)
                    # Update global path variable
                    if "card" in p:
                        global CARD_FILE
                        CARD_FILE = dest
                    else:
                        global SUSP_FILE
                        SUSP_FILE = dest
                    self._refresh_status()

            tk.Button(grid, text="Update…", font=FONT_S,
                      bg=BORDER, fg=TEXT, relief="flat", padx=8, cursor="hand2",
                      command=_browse_ref).grid(row=i, column=2, padx=4)

        # ── Step 3: Run ──────────────────────────────────────────────────────
        self._section(main, "STEP 3 — GENERATE REPORT")

        s3 = tk.Frame(main, bg=CARD, bd=0, relief="flat",
                      highlightbackground=BORDER, highlightthickness=1)
        s3.pack(fill="x", pady=(0, 12))

        btn_row = tk.Frame(s3, bg=CARD)
        btn_row.pack(pady=16, padx=16)

        self._run_btn = tk.Button(
            btn_row, text="⚡  RUN REPORT",
            font=("Georgia", 14, "bold"),
            bg=ACCENT, fg="#0F1923",
            activebackground=ACCENT2,
            relief="flat", padx=32, pady=10,
            cursor="hand2",
            command=self._run_report,
        )
        self._run_btn.pack(side="left", padx=(0, 12))

        self._open_btn = tk.Button(
            btn_row, text="📊  Open Last Report",
            font=FONT_B, bg=CARD, fg=ACCENT,
            activebackground=BORDER,
            relief="flat", padx=16, pady=10,
            cursor="hand2",
            state="disabled",
            command=self._open_last,
        )
        self._open_btn.pack(side="left", padx=(0, 8))

        tk.Button(
            btn_row, text="📁  Reports Folder",
            font=FONT_B, bg=CARD, fg=MUTED,
            activebackground=BORDER,
            relief="flat", padx=16, pady=10,
            cursor="hand2",
            command=lambda: open_folder(REPORTS_DIR),
        ).pack(side="left")

        # ── Progress / log area ──────────────────────────────────────────────
        self._log_var = tk.StringVar(value="Ready.")
        tk.Label(s3, textvariable=self._log_var, font=FONT_S,
                 bg=CARD, fg=MUTED, anchor="w", wraplength=700).pack(
            fill="x", padx=16, pady=(0, 4))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("running.Horizontal.TProgressbar",
                        troughcolor=BORDER, background=ACCENT,   thickness=8)
        style.configure("done.Horizontal.TProgressbar",
                        troughcolor=BORDER, background="#22C55E", thickness=8)
        style.configure("error.Horizontal.TProgressbar",
                        troughcolor=BORDER, background="#DC2626", thickness=8)

        self._progress = ttk.Progressbar(
            s3, mode="indeterminate", length=400,
            style="running.Horizontal.TProgressbar"
        )
        self._progress.pack(pady=(0, 12))

        # ── Results summary ──────────────────────────────────────────────────
        self._result_frame = tk.Frame(main, bg=BG)
        self._result_frame.pack(fill="x")

    def _section(self, parent, title):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", pady=(8, 4))
        tk.Label(f, text=title, font=("Calibri", 9, "bold"),
                 bg=BG, fg=ACCENT).pack(side="left")
        tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x",
                                               expand=True, padx=(8, 0))

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _refresh_status(self):
        # Alpha sheet
        alpha = find_alpha_sheet()
        if alpha:
            self._alpha_var.set(f"✓  {alpha.name}  (modified {date.fromtimestamp(alpha.stat().st_mtime)})")
            self._alpha_lbl.config(fg=GREEN)
        else:
            self._alpha_var.set("⚠  No file found — drop a CSV or XLSX into the watched folder")
            self._alpha_lbl.config(fg=ACCENT)

        # Reference files
        for var, path, lbl_idx in [
            (self._card_var, CARD_FILE, 0),
            (self._susp_var, SUSP_FILE, 1),
        ]:
            if path.exists():
                var.set(f"✓  {path.name}")
                getattr(self, f"_ref_lbl_{lbl_idx}").config(fg=GREEN)
            else:
                var.set(f"✗  NOT FOUND  ({path.name})")
                getattr(self, f"_ref_lbl_{lbl_idx}").config(fg=RED)

        # Re-check every 3 seconds
        self.after(3000, self._refresh_status)

    def _browse_alpha(self):
        chosen = filedialog.askopenfilename(
            title="Select the weekly alpha sheet",
            filetypes=[("CSV / Excel", "*.csv *.xlsx *.xls"), ("All files", "*.*")],
        )
        if chosen:
            import shutil
            dest = WATCHED / Path(chosen).name
            shutil.copy2(chosen, dest)
            self._refresh_status()

    def _run_report(self):
        alpha = find_alpha_sheet()
        if not alpha:
            messagebox.showwarning("No Alpha Sheet",
                "Please drop the weekly entry list into the watched folder first.")
            return
        if not CARD_FILE.exists():
            messagebox.showwarning("Missing File",
                f"Card Numbers file not found:\n{CARD_FILE}")
            return
        if not SUSP_FILE.exists():
            messagebox.showwarning("Missing File",
                f"Suspended List file not found:\n{SUSP_FILE}")
            return

        self._run_btn.config(state="disabled", text="Running…")
        self._progress.config(mode="indeterminate",
                              style="running.Horizontal.TProgressbar", value=0)
        self._progress.start(12)
        self._log("Loading and matching data…")

        # Run in background thread so UI stays responsive
        t = threading.Thread(target=self._worker,
                             args=(str(alpha), str(CARD_FILE), str(SUSP_FILE)),
                             daemon=True)
        t.start()

    def _worker(self, alpha_path, card_path, susp_path):
        try:
            from engine import run_match, build_excel
            self._log("Parsing files…")
            person_map, with_card, without_card, fines_persons, flagged, stats = run_match(alpha_path, card_path, susp_path)
            self._log("Building Excel report…")
            out_name = f"Fines_Card_Verification_{date.today()}.xlsx"
            out_path = str(REPORTS_DIR / out_name)
            build_excel(person_map, with_card, without_card, fines_persons, flagged, stats, out_path)
            self.after(0, self._done, out_path, stats)
        except Exception as e:
            self.after(0, self._error, str(e))

    def _done(self, report_path, stats):
        # Switch to full green "complete" bar
        self._progress.stop()
        self._progress.config(mode="determinate",
                              style="done.Horizontal.TProgressbar",
                              value=100, maximum=100)
        self._run_btn.config(state="normal", text="⚡  RUN REPORT")
        self._last_report = report_path
        self._open_btn.config(state="normal")

        self._log(
            f"✓  Done!  {stats['flagged_names']} flagged  ·  "
            f"{stats['susp_matches']} suspended  ·  "
            f"${stats['total_owed']:,.2f} owed"
        )

        # Results summary cards
        for w in self._result_frame.winfo_children():
            w.destroy()

        cards_data = [
            ("Flagged",        stats["flagged_names"],           RED   if stats["flagged_names"] else GREEN),
            ("Suspended",      stats["susp_matches"],            RED   if stats["susp_matches"]  else GREEN),
            ("With Card #",    stats["with_card"],               ACCENT),
            ("Without Card",   stats["without_card"],            MUTED),
            ("Total $ Owed",   f"${stats['total_owed']:,.2f}",   RED   if stats["total_owed"]    else GREEN),
        ]
        for label, val, color in cards_data:
            box = tk.Frame(self._result_frame, bg=CARD,
                           highlightbackground=color, highlightthickness=2)
            box.pack(side="left", expand=True, fill="x", padx=4, pady=4)
            tk.Label(box, text=str(val), font=("Georgia", 20, "bold"),
                     bg=CARD, fg=color).pack(pady=(10, 2))
            tk.Label(box, text=label, font=FONT_S, bg=CARD, fg=MUTED).pack(pady=(0, 10))

        # Auto-open report
        open_file(report_path)

    def _error(self, msg):
        self._progress.stop()
        self._progress.config(mode="determinate",
                              style="error.Horizontal.TProgressbar",
                              value=100, maximum=100)
        self._run_btn.config(state="normal", text="⚡  RUN REPORT")
        self._log(f"✗  Error: {msg}")
        messagebox.showerror("Error", f"Report failed:\n\n{msg}")

    def _open_last(self):
        if self._last_report and os.path.exists(self._last_report):
            open_file(self._last_report)

    def _log(self, msg: str):
        self._log_var.set(msg)
        self.update_idletasks()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = RodeoCheckerApp()
    app.mainloop()
