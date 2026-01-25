import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials

# --- 1. ตั้งค่าหน้าเว็บและ CSS (5 คอลัมน์สมบูรณ์แบบ) ---
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

# --- 2. การเชื่อมต่อข้อมูล ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(worksheet="Sheet1", ttl="0s")

# ฟังก์ชันบันทึก "เฉพาะจุด" (Surgical Update) - ปรับปรุงใหม่
def update_score_surgical(student_name, day_label, points):
    try:
        # ดึงข้อมูลการเชื่อมต่อ
        conf = st.secrets["connections"]["gsheets"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(conf, scopes=scopes)
        client = gspread.authorize(creds)
        
        # ค้นหาไฟล์ด้วย Spreadsheet ID (ตรวจสอบใน secrets ว่าชื่อ 'spreadsheet' หรือ 'url')
        sheet_id = conf.get("spreadsheet") or conf.get("url")
        sh = client.open_by_key(sheet_id) if len(sheet_id) < 60 else client.open_by_url(sheet_id)
        worksheet = sh.worksheet("Sheet1")
        
        # ค้นหาพิกัด แถว (ชื่อ) และ คอลัมน์ (Day)
        cell_name = worksheet.find(student_name, in_column=1)
        cell_day = worksheet.find(day_label, in_row=1)
        
        if cell_name and cell_day:
            # อ่านค่าเดิมและบวกเพิ่ม
            val = worksheet.cell(cell_name.row, cell_day.col).value
            new_val = int(float(val or 0)) + points
            # บันทึกลงช่องเดียวเป๊ะๆ ห้ามยุ่งช่องอื่น
            worksheet.update_cell(cell_name.row, cell_day.col, new_val)
            return True
        return False
    except Exception as e:
        st.error(f"Error Details: {e}")
        return False

# --- 3. ระบบแอดมิน ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    if st.button("🔓 Admin Login"): st.session_state.show_login = True

if st.session_state.get("show_login") and not st.session_state.logged_in:
    with st.form("login"):
        u, p = st.text_input("ID"), st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u in st.secrets["users"] and p == st.secrets["users"][u]:
                st.session_state.logged_in = True
                st.rerun()

# --- 4. หน้าบันทึกคะแนน ---
if st.session_state.logged_in:
    st.markdown("### 🛡️ บันทึกคะแนน (เจาะจงช่อง F-AK)")
    df = load_data()
    
    with st.form("scoring"):
        names = df.iloc[:, 0].dropna().tolist()
        sel_name = st.selectbox("ชื่อนักเรียน", names)
        days = [c for c in df.columns if "day" in str(c).lower()]
        sel_day = st.selectbox("วันที่/กิจกรรม", days)
        pts = st.number_input("คะแนน", min_value=1, value=5, step=1)
        
        if st.form_submit_button("🚀 ยืนยันบันทึก", use_container_width=True):
            with st.spinner("กำลังบันทึก..."):
                if update_score_surgical(sel_name, sel_day, pts):
                    st.success(f"บันทึกให้ {sel_name} เรียบร้อย!")
                    st.cache_data.clear()
                else:
                    st.error("บันทึกไม่สำเร็จ ตรวจสอบ Spreadsheet ID หรือสิทธิ์การเข้าถึง")

# --- 5. Leaderboard ---
st.markdown("<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)
try:
    df_v = load_data()
    ld = df_v.iloc[:, [0, 37, 38, 39]].copy()
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
except: st.info("กำลังโหลดข้อมูล...")
