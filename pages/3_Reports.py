from datetime import timedelta

import streamlit as st

from core import db, excel_report, timetable
from core.config import BRANCHES, YEARS, SECTIONS, EXPORT_DIR

st.set_page_config(page_title="Reports", layout="wide")
db.init_db()

st.title("Reports")

c1, c2, c3, c4 = st.columns(4)
branch = c1.selectbox("Branch", BRANCHES, key="rep_branch")
year = c2.selectbox("Year", YEARS, key="rep_year")
section = c3.selectbox("Section", SECTIONS, key="rep_section")

# Pichhle 12 mahine
today = timetable.now_ist().date()
months, d = [], today.replace(day=1)
for _ in range(12):
    months.append(d.strftime("%Y-%m"))
    d = (d - timedelta(days=1)).replace(day=1)
month = c4.selectbox("Month", months, key="rep_month")

df = excel_report.month_dataframe(branch, year, section, month)
if df is None:
    st.info("there is no data for the selected class and month.")
else:
    st.dataframe(df, hide_index=True, width="stretch")
    short = df[df["Attendance %"] < 75]
    if len(short):
        st.warning(f"{len(short)} students have attendance less than 75% (Excel mein laal dikhti hai).")
    st.download_button(
        "Download Excel",
        data=excel_report.build_workbook(branch, year, section, month),
        file_name=excel_report.export_filename(branch, year, section, month),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

st.caption(f"after every attendance the excel file is saved here: {EXPORT_DIR}")
