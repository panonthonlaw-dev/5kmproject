import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials

# --- 1. การตั้งค่าหน้าเว็บและ CSS (ล็อก 5 คอลัมน์มืออาชีพ) ---
st.set_page_config(page_title="Patwit Leaderboard", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    [data-testid="block-container"] { padding: 0.8rem 0.2rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body { font-family: 'Sarabun', sans-serif; overflow-x: hidden; background-color: #f8f9fa; }

    .leaderboard-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr) !important;
        grid-auto-rows: 1fr;
        gap: 4px;
        width: 100%;
    }

    .player-card {
        background-color: #ffffff;
        border-radius: 6px;
        padding: 8px 3px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #eee;
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
        height: 100%;
    }

    .player-name {
        font-size: 2.6vw !important;
        font-weight: 600;
        line-height: 1.1;
        height: 5.8vw;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin: 5px 0;
        color: #333;
    }
    
    .score-num { font-size: 5vw !important; font-weight: 800; color: #1E88E5; line-height: 1; }
    .data-val { font-size: 2vw !important; font-weight: 600; color: #444; text-align: right; line-height: 1.1; }
    .rank-tag { font-size: 2.2vw !important; font-weight: 600; opacity: 0.6; }
    .c-1 { color: #FFD700; } .c-2 { color: #999; } .c-3 { color: #CD7F32; }

    @media (min-width: 1024px) {
        .player-card { min-height: 200px; padding: 15px; }
        .player-name { font-size: 1.1rem !important; height: 45px; }
        .score-num { font-size: 2.5rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. การเชื่อมต่อข้อมูล (อ่านแบบ Cache เพื่อความเร็ว) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    return conn.read(worksheet="Sheet1", ttl="0s")

# ฟังก์ชันบันทึก "เฉพาะจุด" (Surgical Update)
def update_single_cell(student_name, day_column, points_to_add):
    try:
        # ดึง Credentials จาก Secrets ที่คุณครูมีอยู่แล้ว
        creds_dict = st.secrets["connections"]["gsheets"]
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # เปิดไฟล์และชีท (เปลี่ยนชื่อไฟล์ให้ตรงกับของคุณครูในสัญญลักษณ์ด้านล่าง)
        sheet = client.open_by_key(st.secrets["connections"]["gsheets"]["spreadsheet"]).worksheet("Sheet1")
        
        # 1. ค้นหาแถวของนักเรียน (ค้นหาจากคอลัมน์ A)
        cell_student = sheet.find(student_name, in_column=1)
        row_index = cell_student.row
        
        # 2. ค้นหาคอลัมน์ของ Day (ค้นหาจากแถวที่ 1)
        cell_day = sheet.find(day_column, in_row=1)
        col_index = cell_day.col
        
        # 3. อ่านค่าปัจจุบันในช่องนั้น
        current_val = sheet.cell(row_index, col_index).value
        new_val = int(float(current_val or 0)) + points_to_add
        
        # 4. บันทึกค่าใหม่ลงไป "ช่องเดียว"
        sheet.update_cell(row_index, col_index, new_val)
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# --- 3. ระบบ Admin ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    if st.button("🔓 Admin Login"):
        st.session_state.show_login = True

if st.session_state.get("show_login") and not st.session_state.logged_in:
    with st.form("login"):
        u, p = st.text_input("ID"), st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u in st.secrets["users"] and p == st.secrets["users"][u]:
                st.session_state.logged_in = True
                st.rerun()

# --- 4. หน้าบันทึกคะแนน (Admin Panel) ---
if st.session_state.logged_in:
    st.markdown("### 🛡️ ระบบบันทึกคะแนน (บันทึกเฉพาะจุด)")
    df = get_full_data()
    
    with st.form("score_entry"):
        names = df.iloc[:, 0].dropna().tolist()
        sel_name = st.selectbox("เลือกนักเรียน", names)
        
        days = [c for c in df.columns if "day" in str(c).lower()]
        sel_day = st.selectbox("เลือกกิจกรรม", days)
        
        points = st.number_input("คะแนน", min_value=1, value=5, step=1)
        
        if st.form_submit_button("🚀 บันทึกคะแนน", use_container_width=True):
            if update_single_cell(sel_name, sel_day, points):
                st.success(f"บันทึกคะแนนให้ {sel_name} ในช่อง {sel_day} สำเร็จ!")
                st.cache_data.clear()
                # ไม่ rerun อัตโนมัติเพื่อให้ครูเห็น Success ก่อน
            else:
                st.error("บันทึกไม่สำเร็จ ตรวจสอบสิทธิ์การเข้าถึงไฟล์")

# --- 5. หน้า Leaderboard (ล็อก 5 คอลัมน์) ---
st.markdown("<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)

try:
    df_view = get_full_data()
    # ดึงเฉพาะคอลัมน์แสดงผลมาโชว์ (A, AL, AM, AN)
    ld = df_view.iloc[:, [0, 37, 38, 39]].copy()
    ld.columns = ['Name', 'Score', 'EXP', 'Medal']
    
    ld['Score'] = pd.to_numeric(ld['Score'], errors='coerce').fillna(0).astype(int)
    ld['EXP'] = pd.to_numeric(ld['EXP'], errors='coerce').fillna(0).astype(int)
    ld['Rank'] = ld['Score'].rank(method='dense', ascending=False).astype(int)
    
    players = ld.sort_values(by=['Rank', 'Name']).to_dict('records')

    grid_h = '<div class="leaderboard-grid">'
    for p in players:
        r = p['Rank']
        icon = "👑" if r <= 3 else "🎖️"
        color_class = f"c-{r}" if r <= 3 else ""
        raw_m = str(p['Medal'])
        formatted_m = raw_m.replace(' ', '<br>', 1) if ' ' in raw_m else raw_m
        
        grid_h += f"""
        <div class="player-card">
            <div class="rank-tag {color_class}">{icon} #{r}</div>
            <div class="player-name">{p['Name']}</div>
            <div>
                <span class="score-num">{p['Score']}</span>
                <div style="font-size:1.8vw; opacity:0.5;">คะแนนรวม</div>
            </div>
            <div style="border-top: 1px solid #eee; padding-top: 5px; margin-top: auto;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="font-size: 1.8vw; color: #888;">EXP:</span>
                    <span class="data-val">{p['EXP']}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="font-size: 1.8vw; color: #888;">ฉายา:</span>
                    <span class="data-val">{formatted_m}</span>
                </div>
            </div>
        </div>"""
    grid_h += '</div>'
    st.markdown(grid_h, unsafe_allow_html=True)
except Exception as e:
    st.info("กำลังโหลดข้อมูลจาก Google Sheets...")
