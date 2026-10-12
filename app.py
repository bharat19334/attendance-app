import streamlit as st

from core import db, timetable

st.set_page_config(
    page_title="Classroom Attendance",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)
db.init_db()

# ---------------------------------------------------------------- THEME
ss = st.session_state
ss.theme = "dark"  # permanent dark theme


def apply_theme():
    """Dark/Light mode CSS + custom styling."""
    if ss.theme == "dark":
        bg = "#0F172A"
        card_bg = "#1E293B"
        text = "#F1F5F9"
        subtext = "#94A3B8"
        border = "#334155"
        accent = "#14B8A6"
    else:
        bg = "#F8FAFC"
        card_bg = "#FFFFFF"
        text = "#0F172A"
        subtext = "#64748B"
        border = "#E2E8F0"
        accent = "#0F766E"

    st.markdown(f"""
    <style>
    .stApp {{
        background-color: {bg};
        color: {text};
    }}
    [data-testid="stSidebar"] {{
        background-color: {card_bg};
        border-right: 1px solid {border};
    }}
    [data-testid="stSidebar"] * {{
        color: {text} !important;
    }}
    h1, h2, h3, h4 {{
        color: {text} !important;
        font-weight: 700 !important;
    }}
    [data-testid="stMetric"] {{
        background-color: {card_bg};
        border: 1px solid {border};
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    [data-testid="stMetricLabel"] {{
        color: {subtext} !important;
        font-size: 0.875rem !important;
    }}
    [data-testid="stMetricValue"] {{
        color: {accent} !important;
        font-size: 2rem !important;
    }}
    .stButton > button {{
        background-color: {accent};
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s;
    }}
    .stButton > button:hover {{
        opacity: 0.9;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }}
    .stTextInput input, .stSelectbox select, .stNumberInput input {{
        background-color: {card_bg} !important;
        color: {text} !important;
        border-radius: 8px !important;
        border: 1px solid {border} !important;
    }}
    [data-testid="stDataFrame"] {{
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid {border};
    }}
    .stAlert {{
        border-radius: 10px;
    }}
    [data-testid="stPageLink"] a {{
        background-color: {card_bg};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 12px 16px;
        color: {text} !important;
        text-decoration: none;
        transition: all 0.2s;
        display: block;
        font-weight: 500;
    }}
    [data-testid="stPageLink"] a:hover {{
        border-color: {accent};
        transform: translateX(4px);
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: {card_bg};
        padding: 6px;
        border-radius: 10px;
        border: 1px solid {border};
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        padding: 8px 16px;
        color: {subtext};
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {accent} !important;
        color: white !important;
    }}
    hr {{
        border-color: {border} !important;
    }}
    </style>
    """, unsafe_allow_html=True)


apply_theme()

# ---------------------------------------------------------------- SIDEBAR
with st.sidebar:
    st.markdown("### 🎓 Attendance System")
    st.markdown("---")

    # (Light/Dark toggle hata diya - theme permanent dark hai)

# ---------------------------------------------------------------- MAIN
now = timetable.now_ist()
total, present = db.today_stats(now.strftime("%Y-%m-%d"))
counts = db.student_counts()

st.title("🎓 Classroom Attendance")
st.caption("Class attendance and Excel reports generated automatically via face recognition.")

c1, c2, c3 = st.columns(3)
c1.metric("👥 Registered students", sum(c["students"] for c in counts))
c2.metric("📋 Today's records", total)
c3.metric("✅ Today present", present)

st.divider()

left, right = st.columns([3, 2])
with left:
    st.subheader("📖 How to use")
    st.markdown(
        """
1. **Register Student**: Fill in the name, roll no., branch/year/section and provide 3-5 face photos (only once).
2. **Take Attendance**: Select the class, take or upload a classroom photo. The period is automatically assigned from the timetable.
3. **Reports**: Download the monthly Excel file. It is also automatically updated in the exports/ folder after every attendance.
"""
    )
    st.markdown("##### 🚀 Quick links")
    st.page_link("pages/1_Register_Student.py", label="👤 Register Student")
    st.page_link("pages/2_Take_Attendance.py", label="📸 Take Attendance")
    st.page_link("pages/3_Reports.py", label="📊 Reports")

with right:
    st.subheader("🏫 Registered classes")
    if counts:
        st.dataframe(
            [{"Branch": c["branch"], "Year": c["year"], "Section": c["section"], "Students": c["students"]} for c in counts],
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("No students registered yet. Please go to the Register Student page.")
    st.caption(f"🕒 {now.strftime('%A, %d %b %Y, %H:%M')}")
