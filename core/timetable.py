"""Timetable: din + time dekhkar subject/period apne aap pata karo.

Apna timetable neeche TIMETABLE mein bharo. Format:
    (branch, year, section): { "Monday": [("HH:MM", "HH:MM", "Subject"), ...], ... }
Jis class ka timetable yahan nahi hoga, uske liye DEFAULT_PERIODS use hoga.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .config import TIMEZONE

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

DEFAULT_PERIODS = [
    ("09:00", "10:00", "Period 1"),
    ("10:00", "11:00", "Period 2"),
    ("11:00", "12:00", "Period 3"),
    ("12:00", "13:00", "Period 4"),
    ("14:00", "15:00", "Period 5"),
    ("15:00", "16:00", "Period 6"),
]

# Example timetable (isko apne asli timetable se badal do)
_CSE_3_A = {
    "Monday":    [("09:00", "10:00", "Python"), ("10:00", "11:00", "DBMS"), ("11:00", "12:00", "Operating Systems"), ("14:00", "16:00", "Python Lab")],
    "Tuesday":   [("09:00", "10:00", "Machine Learning"), ("10:00", "11:00", "Python"), ("11:00", "12:00", "DBMS"), ("14:00", "15:00", "Maths")],
    "Wednesday": [("09:00", "10:00", "Operating Systems"), ("10:00", "11:00", "Machine Learning"), ("11:00", "12:00", "Maths"), ("14:00", "16:00", "DBMS Lab")],
    "Thursday":  [("09:00", "10:00", "DBMS"), ("10:00", "11:00", "Python"), ("11:00", "12:00", "Machine Learning"), ("14:00", "15:00", "Operating Systems")],
    "Friday":    [("09:00", "10:00", "Maths"), ("10:00", "11:00", "Operating Systems"), ("11:00", "12:00", "Python"), ("14:00", "16:00", "ML Lab")],
    "Saturday":  [("09:00", "10:00", "Seminar"), ("10:00", "11:00", "Library")],
}

TIMETABLE: dict[tuple[str, str, str], dict[str, list[tuple[str, str, str]]]] = {
    ("CSE", "3rd Year", "A"): _CSE_3_A,
}


def now_ist() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))


def periods_for(branch: str, year: str, section: str, when: datetime | None = None) -> list[dict]:
    """Us din ke saare periods (start, end, subject, label)."""
    when = when or now_ist()
    weekday = WEEKDAYS[when.weekday()]
    table = TIMETABLE.get((branch, year, section))
    raw = table.get(weekday, []) if table is not None else DEFAULT_PERIODS
    if table is None and weekday == "Sunday":
        raw = []
    return [{"start": s, "end": e, "subject": subj, "label": f"{s}-{e}"} for s, e, subj in raw]


def current_period(branch: str, year: str, section: str, when: datetime | None = None) -> dict | None:
    """Abhi ke time par jo period chal raha hai wo, warna None."""
    when = when or now_ist()
    hhmm = when.strftime("%H:%M")
    for p in periods_for(branch, year, section, when):
        if p["start"] <= hhmm < p["end"]:
            return p
    return None
