"""Excel report: date x period columns, P/A, attendance %. Har attendance ke baad file apne aap update."""
from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill

from . import db
from .config import EXPORT_DIR

HEADER_FILL = PatternFill("solid", fgColor="0F766E")
PRESENT_FILL = PatternFill("solid", fgColor="D1FAE5")
ABSENT_FILL = PatternFill("solid", fgColor="FEE2E2")
SHORTAGE_PCT = 75.0


def _collect(branch, year, section, month, sep):
    records = db.month_records(branch, year, section, month)
    if not records:
        return None

    roster = db.list_students(branch, year, section)
    subject_of: dict[tuple[str, str], str] = {}
    lookup: dict[tuple[int, str, str], str] = {}
    for r in records:
        subject_of[(r["date"], r["period"])] = r["subject"]
        lookup[(r["student_id"], r["date"], r["period"])] = r["status"]
    sessions = sorted(subject_of)

    labels = {}
    for d, p in sessions:
        day = datetime.strptime(d, "%Y-%m-%d").strftime("%d-%b")
        labels[(d, p)] = f"{day}{sep}{subject_of[(d, p)]}{sep}{p}"

    rows = []
    for s in roster:
        row = {"Roll No": s["roll_no"], "Name": s["name"]}
        present = total = 0
        for key in sessions:
            status = lookup.get((s["id"], *key))
            letter = {"Present": "P", "Absent": "A"}.get(status, "-")
            if letter != "-":
                total += 1
                present += letter == "P"
            row[labels[key]] = letter
        row["Present"] = present
        row["Total classes"] = total
        row["Attendance %"] = round(100 * present / total, 1) if total else 0.0
        rows.append(row)
    attendance = pd.DataFrame(rows)

    summary_rows = []
    for key in sessions:
        d, p = key
        statuses = [lookup.get((s["id"], d, p)) for s in roster]
        pres = statuses.count("Present")
        summary_rows.append({
            "Date": d, "Period": p, "Subject": subject_of[key],
            "Present": pres, "Absent": statuses.count("Absent"),
            "Total": pres + statuses.count("Absent"),
        })
    return attendance, pd.DataFrame(summary_rows), len(sessions)


def month_dataframe(branch, year, section, month) -> pd.DataFrame | None:
    """Screen par preview ke liye."""
    result = _collect(branch, year, section, month, sep=" | ")
    return None if result is None else result[0]


def build_workbook(branch, year, section, month) -> bytes | None:
    result = _collect(branch, year, section, month, sep="\n")
    if result is None:
        return None
    attendance, summary, n_sessions = result

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        attendance.to_excel(writer, sheet_name="Attendance", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)

        ws = writer.sheets["Attendance"]
        for cell in ws[1]:
            cell.fill = HEADER_FILL
            cell.font = Font(bold=True, color="FFFFFF")
            cell.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 48
        ws.column_dimensions["A"].width = 11
        ws.column_dimensions["B"].width = 26
        for col in range(3, 3 + n_sessions):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 14
        for col in range(3 + n_sessions, 6 + n_sessions):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 14

        pct_col = 5 + n_sessions
        for row in ws.iter_rows(min_row=2):
            for cell in row[2:2 + n_sessions]:
                cell.alignment = Alignment(horizontal="center")
                if cell.value == "P":
                    cell.fill = PRESENT_FILL
                elif cell.value == "A":
                    cell.fill = ABSENT_FILL
            pct = row[pct_col - 1]
            if isinstance(pct.value, (int, float)) and pct.value < SHORTAGE_PCT:
                pct.font = Font(bold=True, color="B91C1C")
        ws.freeze_panes = "C2"

        ws2 = writer.sheets["Summary"]
        for cell in ws2[1]:
            cell.fill = HEADER_FILL
            cell.font = Font(bold=True, color="FFFFFF")
        for letter, width in zip("ABCDEF", (12, 14, 24, 10, 10, 10)):
            ws2.column_dimensions[letter].width = width
    return buf.getvalue()


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")


def export_filename(branch, year, section, month) -> str:
    return f"attendance_{_safe(branch)}_{_safe(year)}_{_safe(section)}_{month}.xlsx"


def export_month_file(branch, year, section, month) -> Path | None:
    """exports/ folder mein is mahine ki Excel file apne aap likh do (har attendance ke baad)."""
    data = build_workbook(branch, year, section, month)
    if data is None:
        return None
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_DIR / export_filename(branch, year, section, month)
    path.write_bytes(data)
    return path
