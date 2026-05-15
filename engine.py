"""
engine.py  –  Rodeo Checker core matching engine
Produces the Fines_Card_Verification report.
"""

import re
import unicodedata
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import date
import os


# ── Name normalisation ────────────────────────────────────────────────────────

def _norm(text) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.upper().strip()
    text = re.sub(r"[^A-Z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def make_key(last, first) -> str:
    return _norm(str(last)) + "|||" + _norm(str(first))


# ── File parsers ──────────────────────────────────────────────────────────────

def load_alpha_sheet(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(path, on_bad_lines="skip", encoding="utf-8-sig")
    else:
        df = pd.read_excel(path)

    col_map = {}
    for c in df.columns:
        n = _norm(str(c))
        if "RIDER LAST" in n or n == "LAST NAME":
            col_map["last"] = c
        elif "RIDER FIRST" in n or n == "FIRST NAME":
            col_map["first"] = c
        elif "CLASS" in n:
            col_map["class"] = c
        elif "ENTRY TIME" in n or "ENTRY" in n:
            col_map["time"] = c

    rows = []
    for _, r in df.iterrows():
        last  = _norm(str(r.get(col_map.get("last",  "Rider Last Name"),  "")))
        first = _norm(str(r.get(col_map.get("first", "Rider First Name"), "")))
        if not last:
            continue
        rows.append({
            "key":        make_key(last, first),
            "last":       last,
            "first":      first,
            "class_name": str(r.get(col_map.get("class", "Class Name"), "")).strip(),
            "entry_time": str(r.get(col_map.get("time",  "Entry Time"),  "")).strip(),
        })
    return pd.DataFrame(rows)


def load_card_numbers(path: str) -> dict:
    """
    Two member blocks side by side:
      Left:  col0=card#  col1=last  col2=first  col3=city  col4=state  col5=events
      Right: col7=card#  col8=last  col9=first  col10=city col11=state col12=events
    Data starts row index 2.
    Returns dict: key -> list of {card_number, last, first, city, state, events}
    """
    df = pd.read_excel(path, header=None)
    lookup = {}

    def _add(card, last, first, city, state, events):
        l = _norm(str(last))
        f = _norm(str(first))
        if not l or l in ("NAN", "UPRA MEMBERS 2026", "NEW"):
            return
        card_str = str(card).strip().split(".")[0]
        if card_str in ("nan", "NAN", ""):
            return
        k = make_key(l, f)
        entry = {
            "card_number": card_str,
            "last": l, "first": f,
            "city":   str(city).strip()   if str(city)   not in ("nan","NaN") else "",
            "state":  str(state).strip()  if str(state)  not in ("nan","NaN") else "",
            "events": str(events).strip() if str(events) not in ("nan","NaN") else "",
        }
        if entry not in lookup.get(k, []):
            lookup.setdefault(k, []).append(entry)

    for _, r in df.iloc[2:].iterrows():
        vals = r.tolist()
        _add(vals[0], vals[1], vals[2],
             vals[3] if len(vals) > 3 else "",
             vals[4] if len(vals) > 4 else "",
             vals[5] if len(vals) > 5 else "")
        if len(vals) > 7 and pd.notna(vals[7]):
            _add(vals[7],  vals[8],  vals[9],
                 vals[10] if len(vals) > 10 else "",
                 vals[11] if len(vals) > 11 else "",
                 vals[12] if len(vals) > 12 else "")
    return lookup


def load_suspended(path: str) -> dict:
    """
    Row 3 = header (LAST NAME / FIRST NAME / OFFENSE / AMOUNT / EVENT)
    Row 4+ = data.
    Returns dict: key -> list of {last, first, offense, amount, event}
    """
    df = pd.read_excel(path, header=None)
    header_idx = 3
    for i, r in df.iterrows():
        if "LAST NAME" in [_norm(str(v)) for v in r.values]:
            header_idx = i
            break

    lookup = {}
    for _, r in df.iloc[header_idx + 1:].iterrows():
        vals = r.tolist()
        last  = _norm(str(vals[0])) if len(vals) > 0 else ""
        first = _norm(str(vals[1])) if len(vals) > 1 else ""
        if not last or last == "NAN":
            continue
        offense = str(vals[2]).strip() if len(vals) > 2 else ""
        try:
            amount = float(str(vals[3]).replace("$","").replace(",","") or 0)
        except (ValueError, TypeError):
            amount = 0.0
        event = str(vals[4]).strip() if len(vals) > 4 else ""
        k = make_key(last, first)
        lookup.setdefault(k, []).append({
            "last": last, "first": first,
            "offense": offense, "amount": amount, "event": event,
        })
    return lookup


# ── Matching ──────────────────────────────────────────────────────────────────

def run_match(alpha_path: str, card_path: str, susp_path: str):
    alpha     = load_alpha_sheet(alpha_path)
    cards     = load_card_numbers(card_path)
    suspended = load_suspended(susp_path)

    person_map = {}

    for _, rider in alpha.iterrows():
        k     = rider["key"]
        last  = rider["last"]
        first = rider["first"]
        cls   = rider["class_name"]

        card_hits = cards.get(k, [])
        susp_hits = suspended.get(k, [])
        if not card_hits and not susp_hits:
            continue

        if k not in person_map:
            person_map[k] = {
                "last": last, "first": first,
                "classes": set(),
                "card_entries": [],
                "susp_entries": [],
                "on_card_list": False,
                "on_susp_list": False,
            }

        person_map[k]["classes"].add(cls)

        for ch in card_hits:
            person_map[k]["on_card_list"] = True
            entry = {k2: ch[k2] for k2 in ("card_number","events","city","state")}
            if entry not in person_map[k]["card_entries"]:
                person_map[k]["card_entries"].append(entry)

        for sh in susp_hits:
            person_map[k]["on_susp_list"] = True
            person_map[k]["susp_entries"].append({
                "offense": sh["offense"],
                "amount":  sh["amount"],
                "event":   sh["event"],
            })

    detail_rows = []
    src_order = {"Card Numbers": 0, "Suspended List": 1}

    for k, p in person_map.items():
        last   = p["last"]
        first  = p["first"]
        classes = ", ".join(sorted(p["classes"]))
        all_cards_str = ", ".join(e["card_number"] for e in p["card_entries"]) or "—"

        for ce in p["card_entries"]:
            detail_rows.append({
                "last": last, "first": first, "classes": classes,
                "source":      "Card Numbers",
                "card_number": ce["card_number"],
                "all_cards":   all_cards_str,
                "offense":     f"UPRA Member – Events: {ce['events']}",
                "event":       f"{ce['city']}, {ce['state']}".strip(", "),
                "amount":      0.0,
                "on_susp":     p["on_susp_list"],
            })

        for se in p["susp_entries"]:
            detail_rows.append({
                "last": last, "first": first, "classes": classes,
                "source":      "Suspended List",
                "card_number": all_cards_str,
                "all_cards":   all_cards_str,
                "offense":     se["offense"],
                "event":       se["event"],
                "amount":      se["amount"],
                "on_susp":     True,
            })

    detail_rows.sort(key=lambda r: (r["last"], r["first"],
                                    src_order.get(r["source"], 9)))

    totals_rows = []
    for k, p in person_map.items():
        susp_total   = sum(e["amount"]  for e in p["susp_entries"])
        offenses_str = " | ".join(e["offense"] for e in p["susp_entries"]) or "—"
        found_on     = " + ".join(filter(None, [
            "Card #"    if p["on_card_list"] else "",
            "Suspended" if p["on_susp_list"] else "",
        ]))
        classes = ", ".join(sorted(p["classes"]))

        if p["card_entries"]:
            for idx, ce in enumerate(p["card_entries"]):
                totals_rows.append({
                    "last":         p["last"],
                    "first":        p["first"],
                    "classes":      classes,
                    "found_on":     found_on,
                    "card_number":  ce["card_number"],
                    "card_events":  ce["events"],
                    "offenses":     offenses_str,
                    "susp_total":   susp_total,
                    "on_susp":      p["on_susp_list"],
                    "_first":       (idx == 0),
                })
        else:
            totals_rows.append({
                "last":         p["last"],
                "first":        p["first"],
                "classes":      classes,
                "found_on":     found_on,
                "card_number":  "—",
                "card_events":  "—",
                "offenses":     offenses_str,
                "susp_total":   susp_total,
                "on_susp":      p["on_susp_list"],
                "_first":       True,
            })

    totals_rows.sort(key=lambda x: (-x["susp_total"], x["last"], x["first"], x["card_number"]))

    stats = {
        "total_entrants":   len(alpha),
        "flagged_names":    len(person_map),
        "susp_matches":     sum(1 for p in person_map.values() if p["on_susp_list"]),
        "card_matches":     sum(1 for p in person_map.values() if p["on_card_list"]),
        "total_owed":       sum(sum(e["amount"] for e in p["susp_entries"])
                                for p in person_map.values()),
        "total_violations": sum(len(p["susp_entries"]) for p in person_map.values()),
    }

    return detail_rows, totals_rows, stats


# ── Style helpers ─────────────────────────────────────────────────────────────

NAVY  = "1C2B4A"; RED   = "B91C1C"; RED_L  = "FEE2E2"
AMBER = "D97706"; AMB_L = "FEF3C7"; GREEN  = "166534"
GRN_L = "DCFCE7"; SLATE = "475569"; WHITE  = "FFFFFF"
LGREY = "F8FAFC"

def _bd():
    s = Side(style="thin", color="CBD5E1")
    return Border(left=s, right=s, top=s, bottom=s)

def _hdr(ws, row, col, val, bg=NAVY, fg=WHITE, sz=10, bold=True, align="center"):
    c = ws.cell(row=row, column=col, value=val)
    c.font = Font(name="Georgia", bold=bold, color=fg, size=sz)
    c.fill = PatternFill("solid", start_color=bg)
    c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    c.border = _bd()

def _cell(ws, row, col, val, bg=WHITE, bold=False, fmt=None, align="left", fg="000000"):
    c = ws.cell(row=row, column=col, value=val)
    c.font = Font(name="Calibri", bold=bold, color=fg, size=10)
    c.fill = PatternFill("solid", start_color=bg)
    c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    c.border = _bd()
    if fmt:
        c.number_format = fmt


# ── Excel builder ─────────────────────────────────────────────────────────────

def _row_height(texts, col_widths, base=15):
    max_lines = 1
    for text, width in zip(texts, col_widths):
        if not text:
            continue
        cpl = max(1, int(width * 1.6))
        lines = max(1, -(-len(str(text)) // cpl))
        max_lines = max(max_lines, lines)
    return max(base, max_lines * 15)


def build_excel(detail_rows, totals_rows, stats, out_path):
    today_str  = date.today().strftime("%m/%d/%y")
    title_date = f"Fines & Card Verification  {today_str}"
    wb = Workbook()

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 1 — Summary
    # ══════════════════════════════════════════════════════════════════════════
    ws = wb.active
    ws.title = "⚑ Summary"
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A6"

    ws.merge_cells("A1:G1")
    ws.row_dimensions[1].height = 48
    c = ws["A1"]
    c.value = title_date.upper()
    c.font = Font(name="Georgia", bold=True, size=18, color=WHITE)
    c.fill = PatternFill("solid", start_color=NAVY)
    c.alignment = Alignment(horizontal="center", vertical="center")

    ws.row_dimensions[2].height = 6
    ws.row_dimensions[3].height = 36
    ws.row_dimensions[4].height = 20
    ws.row_dimensions[5].height = 8

    for i, (label, val, bg, fg) in enumerate([
        ("ENTRANTS",       stats["total_entrants"],   NAVY,  WHITE),
        ("FLAGGED",        stats["flagged_names"],     RED,   WHITE),
        ("SUSPENDED",      stats["susp_matches"],      RED,   WHITE),
        ("CARD # MATCHES", stats["card_matches"],      AMBER, WHITE),
        ("VIOLATIONS",     stats["total_violations"],  SLATE, WHITE),
        ("TOTAL $ OWED",   f"${stats['total_owed']:,.2f}", GREEN, WHITE),
    ], 1):
        _hdr(ws, 3, i, val,   bg=bg, fg=fg, sz=20, bold=True)
        _hdr(ws, 4, i, label, bg=bg, fg=fg, sz=8,  bold=False)
        ws.column_dimensions[get_column_letter(i)].width = 18

    r = 6
    ws.row_dimensions[r].height = 22
    col_w1 = [22, 22, 14, 12, 14, 40, 14]
    for ci, h in enumerate(["NAME","CLASSES ENTERED","FOUND ON",
                             "CARD #(s)","CARD EVENTS","OFFENSES","TOTAL OWED"], 1):
        _hdr(ws, r, ci, h, bg=SLATE)
        ws.column_dimensions[get_column_letter(ci)].width = col_w1[ci-1]

    seen = set()
    for row in totals_rows:
        pk = (row["last"], row["first"])
        if pk in seen:
            continue
        seen.add(pk)

        all_c  = ", ".join(t["card_number"] for t in totals_rows
                           if (t["last"],t["first"])==pk and t["card_number"] != "—")
        all_ev = ", ".join(dict.fromkeys(
                     t["card_events"] for t in totals_rows
                     if (t["last"],t["first"])==pk and t["card_events"] not in ("—","")
                 ))
        has_fine = row["susp_total"] > 0

        r += 1
        bg = RED_L if row["on_susp"] else AMB_L

        _cell(ws, r, 1, f"{row['last']}, {row['first']}", bg=bg, bold=True)
        _cell(ws, r, 2, row["classes"],        bg=bg)
        _cell(ws, r, 3, row["found_on"],       bg=bg, bold=True, align="center")
        _cell(ws, r, 4, all_c  or "—",        bg=bg, align="center")
        _cell(ws, r, 5, all_ev or "—",        bg=bg)
        _cell(ws, r, 6, row["offenses"] if row["on_susp"] else "—", bg=bg)
        if has_fine:
            _cell(ws, r, 7, row["susp_total"], bg=bg, bold=True,
                  fmt='"$"#,##0.00', align="right", fg=RED)
        else:
            _cell(ws, r, 7, "", bg=bg)

        ws.row_dimensions[r].height = _row_height(
            [f"{row['last']}, {row['first']}", row["classes"], row["found_on"],
             all_c, all_ev, row["offenses"], ""],
            col_w1)

    r += 1
    ws.merge_cells(f"A{r}:F{r}")
    gt = ws.cell(row=r, column=1, value="GRAND TOTAL")
    gt.font  = Font(name="Georgia", bold=True, size=11, color=WHITE)
    gt.fill  = PatternFill("solid", start_color=NAVY)
    gt.alignment = Alignment(horizontal="center", vertical="center")
    gt.border = _bd()
    _cell(ws, r, 7, f"=SUM(G7:G{r-1})", bg=GRN_L, bold=True,
          fmt='"$"#,##0.00', align="right", fg=GREEN)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 2 — All Match Details
    # ══════════════════════════════════════════════════════════════════════════
    ws2 = wb.create_sheet("📋 All Matches")
    ws2.sheet_view.showGridLines = False
    ws2.freeze_panes = "A3"

    ws2.merge_cells("A1:H1")
    ws2.row_dimensions[1].height = 30
    c2 = ws2["A1"]
    c2.value = title_date
    c2.font  = Font(name="Georgia", bold=True, size=13, color=WHITE)
    c2.fill  = PatternFill("solid", start_color=NAVY)
    c2.alignment = Alignment(horizontal="center", vertical="center")

    hdrs2_w = list(zip(
        ["LAST NAME","FIRST NAME","CLASSES ENTERED","MATCHED LIST",
         "CARD #","ALL CARD #(s)","OFFENSE / DESCRIPTION","AMOUNT OWED"],
        [16, 14, 22, 16, 10, 16, 46, 14]
    ))
    for ci, (h, w) in enumerate(hdrs2_w, 1):
        _hdr(ws2, 2, ci, h, bg=SLATE)
        ws2.column_dimensions[get_column_letter(ci)].width = w

    prev2 = None
    for ri, row in enumerate(detail_rows):
        r2 = ri + 3
        is_susp = row["source"] == "Suspended List"
        bg   = RED_L if is_susp else AMB_L
        nm   = (row["last"], row["first"])
        show = nm != prev2
        _cell(ws2, r2, 1, row["last"]    if show else "", bg=bg, bold=show)
        _cell(ws2, r2, 2, row["first"]   if show else "", bg=bg, bold=show)
        _cell(ws2, r2, 3, row["classes"] if show else "", bg=bg)
        _cell(ws2, r2, 4, row["source"],      bg=bg, bold=True, align="center",
              fg=RED if is_susp else AMBER)
        _cell(ws2, r2, 5, row["card_number"], bg=bg, bold=True, align="center")
        _cell(ws2, r2, 6, row["all_cards"],   bg=bg, align="center")
        _cell(ws2, r2, 7, row["offense"],     bg=bg)
        _cell(ws2, r2, 8,
              row["amount"] if row["amount"] else "",
              bg=bg, fmt='"$"#,##0.00' if row["amount"] else None,
              align="right", fg=RED if row["amount"]>0 else "000000")
        ws2.row_dimensions[r2].height = _row_height(
            ["","", row["classes"], row["source"],
             row["card_number"], row["all_cards"], row["offense"], ""],
            [w for _,w in hdrs2_w])
        prev2 = nm

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 3 — Fine Totals
    # ══════════════════════════════════════════════════════════════════════════
    ws3 = wb.create_sheet("✅ Fine Totals")
    ws3.sheet_view.showGridLines = False
    ws3.freeze_panes = "A3"

    ws3.merge_cells("A1:G1")
    ws3.row_dimensions[1].height = 30
    c3 = ws3["A1"]
    c3.value = title_date
    c3.font  = Font(name="Georgia", bold=True, size=13, color=WHITE)
    c3.fill  = PatternFill("solid", start_color=NAVY)
    c3.alignment = Alignment(horizontal="center", vertical="center")

    hdrs3_w = list(zip(
        ["LAST NAME","FIRST NAME","CLASS ENTERED",
         "OFFENSE","EVENT","FINE AMOUNT","PERSON TOTAL"],
        [16, 14, 22, 52, 10, 14, 14]
    ))
    for ci, (h, w) in enumerate(hdrs3_w, 1):
        _hdr(ws3, 2, ci, h, bg=SLATE)
        ws3.column_dimensions[get_column_letter(ci)].width = w
    ws3.row_dimensions[2].height = 30

    from collections import OrderedDict
    fines_by_person = OrderedDict()
    person_meta     = {}

    for row in detail_rows:
        if row["source"] != "Suspended List":
            continue
        pk = (row["last"], row["first"])
        fines_by_person.setdefault(pk, []).append(row)
        person_meta[pk] = row["classes"]

    def person_total(pk):
        return sum(f["amount"] for f in fines_by_person[pk])

    sorted_persons = sorted(fines_by_person.keys(),
                            key=lambda pk: -person_total(pk))

    r3 = 2
    subtotal_row_refs = []

    FINE_BG    = "FEE2E2"
    SUBTOT_BG  = "1C2B4A"
    SUBTOT_FG  = "FFFFFF"

    for pk in sorted_persons:
        last, first = pk
        fines   = fines_by_person[pk]
        classes = person_meta[pk]

        fine_start_row = None
        fine_end_row   = None

        for fi, fine in enumerate(fines):
            r3 += 1
            if fine_start_row is None:
                fine_start_row = r3
            fine_end_row = r3

            show_name = (fi == 0)
            _cell(ws3, r3, 1, last    if show_name else "", bg=FINE_BG, bold=show_name)
            _cell(ws3, r3, 2, first   if show_name else "", bg=FINE_BG, bold=show_name)
            _cell(ws3, r3, 3, classes if show_name else "", bg=FINE_BG)
            _cell(ws3, r3, 4, fine["offense"], bg=FINE_BG)
            _cell(ws3, r3, 5, fine["event"],   bg=FINE_BG, align="center")
            _cell(ws3, r3, 6, fine["amount"],  bg=FINE_BG, bold=True,
                  fmt='"$"#,##0.00', align="right", fg=RED)
            _cell(ws3, r3, 7, "", bg=FINE_BG)
            ws3.row_dimensions[r3].height = _row_height(
                [last, first, classes, fine["offense"], fine["event"], "", ""],
                [w for _,w in hdrs3_w])

        r3 += 1
        subtotal_row_refs.append(r3)
        _cell(ws3, r3, 7,
              f"=SUM(F{fine_start_row}:F{fine_end_row})",
              bg=GRN_L, bold=True, fmt='"$"#,##0.00', align="right", fg=GREEN)
        navy_fill = PatternFill("solid", start_color=SUBTOT_BG)
        for ci in range(1, 7):
            c = ws3.cell(row=r3, column=ci)
            c.value = None
            c.fill  = navy_fill
            c.border = _bd()
        ws3.merge_cells(f"A{r3}:F{r3}")
        sub = ws3.cell(row=r3, column=1)
        sub.value     = f"TOTAL  —  {last}, {first}"
        sub.font      = Font(name="Georgia", bold=True, size=10, color=SUBTOT_FG)
        sub.fill      = navy_fill
        sub.alignment = Alignment(horizontal="right", vertical="center", indent=1)
        sub.border    = _bd()
        ws3.row_dimensions[r3].height = 18

        r3 += 1
        for ci in range(1, 8):
            ws3.cell(row=r3, column=ci).fill = PatternFill("solid", start_color="FFFFFF")
        ws3.row_dimensions[r3].height = 5

    r3 += 1
    if subtotal_row_refs:
        formula = "+".join(f"G{sr}" for sr in subtotal_row_refs)
        _cell(ws3, r3, 7, f"={formula}",
              bg=GRN_L, bold=True, fmt='"$"#,##0.00', align="right", fg=GREEN)
    navy_fill2 = PatternFill("solid", start_color=NAVY)
    for ci in range(1, 7):
        c = ws3.cell(row=r3, column=ci)
        c.value = None
        c.fill  = navy_fill2
        c.border = _bd()
    ws3.merge_cells(f"A{r3}:F{r3}")
    gtr = ws3.cell(row=r3, column=1)
    gtr.value     = "GRAND TOTAL — ALL FINES"
    gtr.font      = Font(name="Georgia", bold=True, size=11, color=WHITE)
    gtr.fill      = navy_fill2
    gtr.alignment = Alignment(horizontal="center", vertical="center")
    gtr.border    = _bd()
    ws3.row_dimensions[r3].height = 22

    wb.save(out_path)
    return out_path
