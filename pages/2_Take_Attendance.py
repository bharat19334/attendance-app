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
st.caption(f"{now.strftime('%A, %d %b %Y, %H:%M')} | Is class mein {len(roster)} students registered hain.")

# --------------------------------------------------------------- 2. period
st.subheader("Period")
mode = st.radio("Period kaise chunna hai", ["Timetable se auto", "Manual"], horizontal=True, key="att_mode")
subject = period = ""

if mode == "Timetable se auto":
    current = timetable.current_period(branch, year, section, now)
    if current:
        subject, period = current["subject"], current["label"]
        st.success(f"Abhi chal raha hai: {subject} ({period})")
    else:
        st.warning("Abhi timetable mein koi period nahi chal raha. Manual mode chuno.")
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
    uploaded = st.file_uploader("Classroom ki photo", type=["jpg", "jpeg", "png"], key="att_upload")
with tab_cam:
    shot = st.camera_input("Classroom ki photo", key="att_cam")
photo = uploaded or shot

with st.expander("Settings (zarurat ho toh)"):
    tolerance = st.slider("Match strictness (chhota = strict)", 0.35, 0.70, DEFAULT_TOLERANCE, 0.01, key="att_tol")
    upsample = st.slider("Chhote chehre dhoondhne ke liye zoom (zyada = slow)", 1, 3, 1, key="att_ups")

if not roster:
    st.error("Is class mein koi student registered nahi hai. Pehle Register Student page par jao.")

ready = bool(roster and subject and period and photo)
if st.button("Mark attendance", type="primary", disabled=not ready):
    with st.spinner("Chehre pehchane ja rahe hain..."):
        try:
            result = face_engine.recognize_faces(photo.getvalue(), roster, tolerance, upsample)
        except ValueError as exc:
            st.error(str(exc))
            result = None
    if result is not None:
        db.save_session([s["id"] for s in roster], list(result["matched"]), subject, period, today)
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
        st.warning("Excel file update nahi hui (shayad wo Excel mein khuli hai). Band karke Reports page se download karo.")
    if r["unknown"]:
        st.warning(f"{r['unknown']} chehre kisi registered student se match nahi hue. "
                   "Neeche table mein status khud theek kar sakte ho.")

    st.image(r["annotated"], caption="Hara = pehchana gaya, laal = unknown", width="stretch")

    df = pd.DataFrame(
        [{"student_id": x["student_id"], "Roll No": x["roll_no"], "Name": x["name"], "Status": x["status"]} for x in rows]
    )
    st.markdown("**Galti ho toh Status badlo, phir Save corrections dabao.**")
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
        ss.att_msg = f"{changed} changes save ho gaye." if changed else "Koi change nahi tha."
        st.rerun()
