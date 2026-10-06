import pandas as pd
import streamlit as st

from core import db, excel_report, face_engine, timetable
from core.config import BRANCHES, YEARS, SECTIONS, DEFAULT_TOLERANCE

st.set_page_config(page_title="Take Attendance", layout="wide")
db.init_db()
ss = st.session_state
ss.setdefault("att_editor_n", 0)

st.title("Take attendance")

now = timetable.now_ist()
today = now.strftime("%Y-%m-%d")

# ---------------------------------------------------------------- 1. class
c1, c2, c3 = st.columns(3)
branch = c1.selectbox("Branch", BRANCHES, key="att_branch")
year = c2.selectbox("Year", YEARS, key="att_year")
section = c3.selectbox("Section", SECTIONS, key="att_section")
roster = db.list_students(branch, year, section, with_embeddings=True)
st.caption(f"{now.strftime('%A, %d %b %Y, %H:%M')} | In this class {len(roster)} students are registered.")

# --------------------------------------------------------------- 2. period
st.subheader("Period")
mode = st.radio("how to choice a period", [" auto from timetable", "Manual"], horizontal=True, key="att_mode")
subject = period = ""

if mode == "Timetable se auto":
    current = timetable.current_period(branch, year, section, now)
    if current:
        subject, period = current["subject"], current["label"]
        st.success(f"it's going on: {subject} ({period})")
    else:
        st.warning("period is not available in timetable. choose manually mode.")
else:
    todays = timetable.periods_for(branch, year, section, now)
    options = {f"{p['label']} - {p['subject']}": p for p in todays}
    pick = st.selectbox("Aaj ke periods", list(options) + ["Custom (extra class)"], key="att_pick")
    if pick in options:
        subject, period = options[pick]["subject"], options[pick]["label"]
    else:
        subject = st.text_input("Subject", key="att_custom_subject").strip()
        period = st.text_input("Time / period (jaise 16:00-17:00)", key="att_custom_period").strip()

# ---------------------------------------------------------------- 3. photo
st.subheader("Classroom photo")
tab_up, tab_cam = st.tabs(["Photo upload", "Camera"])
with tab_up:
    uploaded = st.file_uploader("photo of classroom", type=["jpg", "jpeg", "png"], key="att_upload")
with tab_cam:
    shot = st.camera_input("photo of classroom", key="att_cam")
photo = uploaded or shot

with st.expander("Settings (zarurat ho toh)"):
    tolerance = st.slider("Match strictness (small = strict)", 0.35, 0.70, DEFAULT_TOLERANCE, 0.01, key="att_tol")
    upsample = st.slider("zoom for small face recognition (more = slow)", 1, 3, 1, key="att_ups")

if not roster:
    st.error("in this class no students are registered. first go to the register students page.")

ready = bool(roster and subject and period and photo)
if st.button("Mark attendance", type="primary", disabled=not ready):
    with st.spinner("face is being recognized..."):
        try:
            result = face_engine.recognize_faces(photo.getvalue(), roster, tolerance, upsample)
        except ValueError as exc:
            st.error(str(exc))
            result = None
    if result is not None:
        db.save_session([s["id"] for s in roster], list(result["matched"]), subject, period, today)

        try:
            from core import google_sheet
            rows = db.session_rows(branch, year, section, today, period)
            n = google_sheet.sync_attendance(rows, subject, period, today)
            st.toast(f"✅ {n} row saved to Google Sheet", icon="📊")
        except FileNotFoundError:
            st.warning("Google Sheet sync skip — I couldn't find the credentials.json file.")
        except Exception as e:
            st.warning(f"Google Sheet sync fail: {e}")
            
        export_error = None
        try:
            excel_report.export_month_file(branch, year, section, today[:7])
        except OSError as exc:
            export_error = str(exc)
        ss.att_result = {
            "branch": branch, "year": year, "section": section, "date": today,
            "period": period, "subject": subject, "annotated": result["annotated"],
            "n_faces": result["n_faces"], "unknown": result["unknown"], "export_error": export_error,
        }
        ss.att_editor_n += 1

# --------------------------------------------------------------- 4. result
r = ss.get("att_result")
if r:
    st.divider()
    st.subheader(f"{r['branch']} {r['year']} {r['section']} | {r['subject']} ({r['period']}) | {r['date']}")
    rows = db.session_rows(r["branch"], r["year"], r["section"], r["date"], r["period"])
    n_present = sum(1 for x in rows if x["status"] == "Present")

    if ss.get("att_msg"):
        st.success(ss.pop("att_msg"))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Present", n_present)
    m2.metric("Absent", len(rows) - n_present)
    m3.metric("Chehre mile", r["n_faces"])
    m4.metric("Unknown chehre", r["unknown"])

    if r["export_error"]:
        st.warning("The Excel file didn't update (maybe it's open in Excel). Close it and download it from the Reports page")
    if r["unknown"]:
        st.warning(f"{r['unknown']} The face did not match any registered student. You can correct the status in the table below yourself.")

    st.image(r["annotated"], caption="Hara = Recognized laal = unknown", width="stretch")

    df = pd.DataFrame(
        [{"student_id": x["student_id"], "Roll No": x["roll_no"], "Name": x["name"], "Status": x["status"]} for x in rows]
    )
    st.markdown("**If there's an error, change the status and then click Save corrections.**")
    edited = st.data_editor(
        df,
        key=f"att_editor_{ss.att_editor_n}",
        hide_index=True,
        width="stretch",
        disabled=["Roll No", "Name"],
        column_config={
            "student_id": None,
            "Status": st.column_config.SelectboxColumn("Status", options=["Present", "Absent"], required=True),
        },
    )
    if st.button("Save corrections"):
        changed = 0
        original = dict(zip(df["student_id"], df["Status"]))
        for _, row in edited.iterrows():
            if row["Status"] != original[row["student_id"]]:
                db.set_status(int(row["student_id"]), r["subject"], r["period"], r["date"], row["Status"])
                changed += 1
        try:
            excel_report.export_month_file(r["branch"], r["year"], r["section"], r["date"][:7])
        except OSError:
            pass
        ss.att_editor_n += 1
        ss.att_msg = f"{changed} changes saved." if changed else "No changes were made."
        st.rerun()
