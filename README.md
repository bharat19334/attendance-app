# Classroom Attendance (Streamlit + Face Recognition)

Teacher classroom ki photo leta hai, system chehre pehchaan kar Present/Absent lagata hai,
aur Excel report apne aap update hoti rehti hai.

## Chalane ka tarika

Python 3.9 - 3.12 chahiye.

```bash
python -m venv .venv
# Windows:   .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Browser mein `http://localhost:8501` khulega. Camera sirf `localhost` ya `https` par chalta hai.

## Use karna

1. **Register Student**: naam, roll no., branch/year/section aur 3-5 face photos (ek baar).
2. **Take Attendance**: class chuno -> period timetable se apne aap lagta hai -> classroom photo
   upload/camera -> *Mark attendance*. Galti ho toh table mein Status badlo aur *Save corrections* dabao.
3. **Reports**: mahine ki Excel dekho/download karo. Har attendance ke baad ek Excel file `exports/`
   folder mein apne aap update bhi hoti hai (Excel mein khuli ho toh band kar do).

## Apne hisaab se badalna

| Kya | Kahan |
|---|---|
| Branch / year / section list, strictness | `core/config.py` |
| Timetable (din + time -> subject) | `core/timetable.py` (`TIMETABLE` dict) |
| Excel ka format | `core/excel_report.py` |

Jis class ka timetable `TIMETABLE` mein nahi hai, uske liye 6 default periods (Period 1-6) lagte hain
(Sunday ko koi nahi). Period manually bhi chun sakte ho.

## Folder structure

```
attendance-app/
├── app.py                      # Home
├── pages/
│   ├── 1_Register_Student.py
│   ├── 2_Take_Attendance.py
│   └── 3_Reports.py
├── core/
│   ├── config.py               # settings
│   ├── db.py                   # SQLite (students, attendance)
│   ├── face_engine.py          # chehra detect + match
│   ├── timetable.py            # din/time -> subject
│   └── excel_report.py         # Excel report
├── data/                       # attendance.db yahin banta hai
├── exports/                    # auto-updated Excel files
├── .streamlit/config.toml
└── requirements.txt
```

## Accuracy ke liye tips

- Registration mein achhi roshni, seedhi photos (seedha, thoda left, thoda right).
- Classroom photo saamne se lo, chehre bade dikhein. Bahut peeche wale chehre chhote hone se miss ho sakte
  hain (Settings mein zoom slider badhao, ya ek period mein 2 photos lo; Present wapas Absent nahi hota).
- Match nahi hua toh Status khud theek kar do. Unknown chehre review ke liye dikhte hain.

## Privacy

Face data biometric hota hai. Students ki sahmati lo, `data/attendance.db` safe rakho aur kisi se share mat karo.

## Agar `pip install dlib-bin` fail ho

Python 3.12 se naye version par wheel na mile toh Python 3.11/3.12 ka virtual environment banao.
