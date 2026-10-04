import streamlit as st

from core import db, face_engine
from core.config import BRANCHES, YEARS, SECTIONS, MIN_REG_PHOTOS, MAX_REG_PHOTOS

st.set_page_config(page_title="Register Student", layout="wide")
db.init_db()
ss = st.session_state

ss.setdefault("reg_photos", [])   # photos (bytes) jo abhi tak add hui
ss.setdefault("reg_nonce", 0)     # form reset ke liye
ss.setdefault("cam_n", 0)
ss.setdefault("upl_n", 0)
ss.setdefault("reg_flash", None)


def add_camera_photo():
    shot = ss.get(f"cam_{ss.cam_n}")
    if shot is not None and len(ss.reg_photos) < MAX_REG_PHOTOS:
        ss.reg_photos.append(shot.getvalue())
    ss.cam_n += 1  # camera widget reset


def add_uploaded_photos():
    for f in ss.get(f"upl_{ss.upl_n}") or []:
        if len(ss.reg_photos) >= MAX_REG_PHOTOS:
            break
        ss.reg_photos.append(f.getvalue())
    ss.upl_n += 1


def remove_photo(i: int):
    del ss.reg_photos[i]


st.title("Register student")

if ss.reg_flash:
    st.success(ss.reg_flash)
    ss.reg_flash = None

n = ss.reg_nonce
left, right = st.columns(2, gap="large")

with left:
    st.subheader("Student details")
    name = st.text_input("Name", key=f"name_{n}")
    roll_no = st.text_input("Roll number", key=f"roll_{n}")
    branch = st.selectbox("Branch", BRANCHES, key="reg_branch")
    year = st.selectbox("Year", YEARS, key="reg_year")
    section = st.selectbox("Section", SECTIONS, key="reg_section")

with right:
    st.subheader(f"Face photos ({len(ss.reg_photos)}/{MAX_REG_PHOTOS})")
    st.caption(
        f"{MIN_REG_PHOTOS}-{MAX_REG_PHOTOS} photos: seedha, thoda left, thoda right. "
        "Roshni achhi ho aur photo mein sirf ek chehra ho."
    )
    tab_cam, tab_upl = st.tabs(["Camera", "Upload"])
    with tab_cam:
        st.camera_input("Camera se photo lo", key=f"cam_{ss.cam_n}")
        st.button("Add this photo", on_click=add_camera_photo,
                  disabled=len(ss.reg_photos) >= MAX_REG_PHOTOS, key="add_cam")
    with tab_upl:
        st.file_uploader("Photos chuno", type=["jpg", "jpeg", "png"], accept_multiple_files=True,
                         key=f"upl_{ss.upl_n}")
        st.button("Add uploaded photos", on_click=add_uploaded_photos,
                  disabled=len(ss.reg_photos) >= MAX_REG_PHOTOS, key="add_upl")

    if ss.reg_photos:
        cols = st.columns(MAX_REG_PHOTOS)
        for i, data in enumerate(ss.reg_photos):
            with cols[i]:
                st.image(data, width="stretch")
                st.button("Remove", key=f"rm_{i}", on_click=remove_photo, args=(i,))

st.divider()
if st.button("Save student", type="primary"):
    name_v, roll_v = name.strip(), roll_no.strip()
    if not name_v or not roll_v:
        st.error("Name aur roll number dono bharo.")
    elif len(ss.reg_photos) < MIN_REG_PHOTOS:
        st.error(f"Kam se kam {MIN_REG_PHOTOS} photos chahiye (abhi {len(ss.reg_photos)} hain).")
    else:
        embeddings, problems = [], []
        with st.spinner("Chehre check ho rahe hain..."):
            for i, data in enumerate(ss.reg_photos, start=1):
                emb, err = face_engine.encode_registration_photo(data)
                if emb is None:
                    problems.append(f"Photo {i}: {err}")
                else:
                    embeddings.append(emb)
        if len(embeddings) < MIN_REG_PHOTOS:
            st.error(f"Sirf {len(embeddings)} photos sahi nikli, kam se kam {MIN_REG_PHOTOS} chahiye. "
                     "Kharab photos hata kar nayi add karo.")
            for p in problems:
                st.warning(p)
        else:
            try:
                db.add_student(name_v, roll_v, branch, year, section, embeddings)
            except ValueError as exc:
                st.error(str(exc))
            else:
                ss.reg_flash = f"{name_v} ({roll_v}) register ho gaya, {len(embeddings)} face photos ke saath."
                ss.reg_photos = []
                ss.reg_nonce += 1
                ss.cam_n += 1
                ss.upl_n += 1
                st.rerun()

st.divider()
st.subheader("Registered students")
students = db.list_students()
if not students:
    st.info("Abhi koi student nahi hai.")
else:
    st.dataframe(
        [{"Roll No": s["roll_no"], "Name": s["name"], "Branch": s["branch"], "Year": s["year"],
          "Section": s["section"], "Face photos": s["photos"]} for s in students],
        hide_index=True,
        width="stretch",
    )
    
