import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. ป้องกัน AttributeError: ตั้งค่าตัวแปรเริ่มต้นทันทีที่เปิดแอป ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "admin_name" not in st.session_state: st.session_state.admin_name = ""
if "show_login" not in st.session_state: st.session_state.show_login = False

# --- 2. ตั้งค่าหน้าเว็บและ CSS (5 คอลัมน์สมบูรณ์แบบ) ---
st.set_page_config(page_title="Patwit Leaderboard", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    [data-testid="block-container"] { padding: 0.8rem 0.2rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body { font-family: 'Sarabun', sans-serif; overflow-x: hidden; background-color: #f8f9fa; }
    .leaderboard-grid { display: grid; grid-template-columns: repeat(5, 1fr) !important; grid-auto-rows: 1fr; gap: 4px; }
    .player-card { background-color: #fff; border-radius: 6px; padding: 8px 3px; text-align: center; border: 1px solid #eee; display: flex; flex-direction: column; justify-content: space-between; height: 100%; }
    .player-name { font-size: 2.6vw !important; font-weight: 600; line-height: 1.1; height: 5.8vw; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin: 5px 0; }
    .score-num { font-size: 5vw !important; font-weight: 800; color: #1E88E5; line-height: 1; }
    .data-val { font-size: 2vw !important; font-weight: 600; color: #444; text-align: right; }
    .rank-tag { font-size: 2.2vw !important; font-weight: 600; opacity: 0.6; }
    .c-1 { color: #FFD700; } .c-2 { color: #999; } .c-3 { color: #CD7F32; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. การเชื่อมต่อข้อมูล ---
def get_gspread_client():
    conf = st.secrets["connections"]["gsheets"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(conf, scopes=scopes)
    return gspread.authorize(creds)

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(worksheet="Sheet1", ttl="0s")

# ฟังก์ชันบันทึก "เฉพาะจุด" และ "บันทึก Logs" (ห้ามลบส่วนอื่น)
def update_score_and_log(student_name, day_label, points, admin_name):
    try:
        client = get_gspread_client()
        conf = st.secrets["connections"]["gsheets"]
        sheet_id = conf.get("spreadsheet") or conf.get("url")
        sh = client.open_by_key(sheet_id) if len(sheet_id) < 60 else client.open_by_url(sheet_id)
        
        # 1. บันทึกคะแนนลง Sheet1 (เจาะจงช่องเดียว)
        ws = sh.worksheet("Sheet1")
        row = ws.find(student_name, in_column=1).row
        col = ws.find(day_label, in_row=1).col
        curr_val = ws.cell(row, col).value
        new_val = int(float(curr_val or 0)) + points
        ws.update_cell(row, col, new_val)
        
        # 2. บันทึกประวัติลง Logs
        log_ws = sh.worksheet("Logs")
        log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), admin_name, student_name, day_label, points, "Success"])
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
        return False

# --- 4. ระบบล็อกอิน ---
h_l, h_r = st.columns([20, 1])
with h_r:
    if not st.session_state.logged_in:
        if st.button("🔓"): st.session_state.show_login = not st.session_state.show_login
    else:
        if st.button("🚪"): 
            st.session_state.logged_in = False
            st.session_state.admin_name = ""
            st.rerun()

if st.session_state.show_login and not st.session_state.logged_in:
    _, l_col, _ = st.columns([1, 1, 1])
    with l_col:
        with st.form("login_form"):
            u = st.text_input("Admin ID")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state.logged_in = True
                    st.session_state.admin_name = u
                    st.session_state.show_login = False
                    st.rerun()
                else: st.error("ID หรือ Password ผิดครับ")

# --- 5. ส่วนจัดการคะแนนสำหรับแอดมิน ---
# ตรวจสอบก่อนว่า logged_in เป็น True และ admin_name ไม่ว่าง
if st.session_state.logged_in and st.session_state.admin_name:
    st.markdown(f"#### 🛡️ แอดมิน: {st.session_state.admin_name}")
    df_admin = load_data()
    
    with st.expander("🎯 บันทึกคะแนนใหม่ (ห้ามลบ ห้ามทับส่วนอื่น)", expanded=True):
        names = df_admin.iloc[:, 0].dropna().tolist()
        sel_name = st.selectbox("เลือกนักเรียน", names)
        days = [c for c in df_admin.columns if "day" in str(c).lower()]
        sel_day = st.selectbox("เลือกกิจกรรม", days)
        pts = st.number_input("คะแนนที่เพิ่ม", min_value=1, value=5, step=1)
        
        if st.button("🚀 ยืนยันบันทึกคะแนน", use_container_width=True):
            if update_score_and_log(sel_name, sel_day, pts, st.session_state.admin_name):
                st.success(f"บันทึกให้ {sel_name} สำเร็จ!")
                st.cache_data.clear()

# --- 6. หน้า Leaderboard (แสดงผล 5 คอลัมน์) ---
st.markdown("<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)



try:
    df_view = load_data()
    # ดึง Name(A), Score(AL), EXP(AM), Medal(AN)
    ld = df_view.iloc[:, [0, 37, 38, 39]].copy()
    ld.columns = ['Name', 'Score', 'EXP', 'Medal']
    ld['Score'] = pd.to_numeric(ld['Score'], errors='coerce').fillna(0).astype(int)
    ld['EXP'] = pd.to_numeric(ld['EXP'], errors='coerce').fillna(0).astype(int)
    ld['Rank'] = ld['Score'].rank(method='dense', ascending=False).astype(int)
    
    players = ld.sort_values(by=['Rank', 'Name']).to_dict('records')
    grid_h = '<div class="leaderboard-grid">'
    for p in players:
        r, icon = p['Rank'], ("👑" if p['Rank'] <= 3 else "🎖️")
        color = f"c-{r}" if r <= 3 else ""
        medal = str(p['Medal']).replace(' ', '<br>', 1)
        grid_h += f"""
        <div class="player-card">
            <div class="rank-tag {color}">{icon} #{r}</div>
            <div class="player-name">{p['Name']}</div>
            <div><span class="score-num">{p['Score']}</span><div style="font-size:1.8vw; opacity:0.5;">คะแนนรวม</div></div>
            <div style="border-top: 1px solid #eee; padding-top: 5px; margin-top: auto;">
                <div style="display: flex; justify-content: space-between;"><span style="font-size: 1.8vw; color: #888;">EXP:</span><span class="data-val">{p['EXP']}</span></div>
                <div style="display: flex; justify-content: space-between;"><span style="font-size: 1.8vw; color: #888;">ฉายา:</span><span class="data-val">{medal}</span></div>
            </div>
        </div>"""
    st.markdown(grid_h + '</div>', unsafe_allow_html=True)
except: st.info("กำลังโหลดข้อมูลจากระบบ...")
