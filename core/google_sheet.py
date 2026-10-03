import os
from datetime import datetime
import streamlit as st    # ← Ye add karo

import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------- config
SHEET_ID = "14t3gA3Wn0aPNLwP91NFYPZqF27nUHmKJpTjABolsv_o"   # ← Ye change karo
WORKSHEET_NAME = "Attendance"
CREDS_FILE = "credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Timestamp", "Roll No", "Name", "Branch",
    "Year", "Section", "Status", "Subject", "Period", "Date",
]

_client = None


def _get_sheet():
    """Sheet ko lazy load karo (local ya Streamlit Cloud dono pe kaam kare)."""
    global _client
    if _client is None:
        # Streamlit Cloud pe secrets se padho
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=SCOPES,
            )
        # Local pe file se padho
        elif os.path.exists(CREDS_FILE):
            creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
        else:
            raise FileNotFoundError(
                "Google credentials not found. Local: place credentials.json in project root. "
                "Cloud: add [gcp_service_account] in Streamlit secrets."
            )
        _client = gspread.authorize(creds)

    sheet = _client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)

    if not sheet.get_all_values():
        sheet.append_row(HEADERS)

    return sheet


def sync_attendance(rows, subject: str, period: str, date: str) -> int:
    """
    rows: db.session_rows() ka output — [{"roll_no", "name", "status", ...}, ...]
    Ek hi sheet mein saari rows append karta hai.
    Return: kitni rows add hui
    """
    sheet = _get_sheet()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    payload = []
    for r in rows:
        payload.append([
            timestamp,
            r.get("roll_no", ""),
            r.get("name", ""),
            r.get("branch", ""),
            r.get("year", ""),
            r.get("section", ""),
            r.get("status", ""),
            subject,
            period,
            date,
        ])

    if payload:
        sheet.append_rows(payload, value_input_option="USER_ENTERED")
    return len(payload)