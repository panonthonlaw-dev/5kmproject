import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. ตั้งค่าพื้นฐานและตัวแปรเริ่มต้น ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "admin_name" not in st.session_state: st.session_state.admin_name = ""
if "show_login" not in st.session_state: st.session_state.show_login = False

st.set_page_config(page_title="Patwit Leaderboard", layout="wide")

# CSS: ล็อก 5 คอลัมน์สมดุลบนมือถือ
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

# --- 2. ฟังก์ชันการเชื่อมต่อ (gspread สำหรับการเขียน และ gsheets สำหรับการอ่าน) ---
def get_gspread_sh():
    conf = st.secrets["connections"]["gsheets"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(conf, scopes=scopes)
    client = gspread.authorize(creds)
    sheet_id = conf.get("spreadsheet") or conf.get("url")
    # ตรวจสอบว่าเป็น URL หรือ ID
    if "docs.google.com" in sheet_id: return client.open_by_url(sheet_id)
    return client.open_by_key(sheet_id)

def load_view_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(worksheet="Sheet1", ttl="0s")

# --- 3. ระบบ Authentication ---
h_l, h_r = st.columns([20, 1])
with h_r:
    if not st.session_state.logged_in:
        if st.button("🔓"): st.session_state.show_login = not st.session_state.show_login
    else:
        if st.button("🚪"): 
            st.session_state.logged_in = False
            st.rerun()

if st.session_state.show_login and not st.session_state.logged_in:
    _, l_col, _ = st.columns([1, 1, 1])
    with l_col:
        with st.form("login"):
            u, p = st.text_input("Admin ID"), st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state.logged_in = True
                    st.session_state.admin_name = u
                    st.session_state.show_login = False
                    st.rerun()
                else: st.error("ข้อมูลไม่ถูกต้อง")

# --- 4. ส่วน Admin: บันทึกคะแนน + ป้องกันบันทึกซ้ำ + ระบบ Log ---
if st.session_state.logged_in:
    st.markdown(f"#### 🛡️ แอดมิน: {st.session_state.admin_name}")
    df_main = load_view_data()
    
    with st.expander("🎯 บันทึกคะแนนใหม่", expanded=True):
        sel_name = st.selectbox("เลือกนักเรียน", df_main.iloc[:, 0].dropna().tolist())
        days = [c for c in df_main.columns if "day" in str(c).lower()]
        sel_day = st.selectbox("เลือกช่องลงคะแนน (Day)", days)
        pts = st.number_input("คะแนน", min_value=1, value=5, step=1)

        # --- ระบบตรวจสอบการบันทึกซ้ำ (ตรวจสอบจาก Logs สดๆ) ---
        sh = get_gspread_sh()
        log_ws = sh.worksheet("Logs")
        logs_raw = log_ws.get_all_records()
        logs_df = pd.DataFrame(logs_raw)
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        is_duplicate = False

        if not logs_df.empty:
            # ล็อกที่: ชื่อนักเรียนตรงกัน + ช่อง Day ตรงกัน + วันที่ (Timestamp) ตรงกับวันนี้
            # แปลง Timestamp ใน log ให้เป็นแค่วันที่เพื่อเช็คซ้ำ
            logs_df['Date_Only'] = pd.to_datetime(logs_df['Timestamp']).dt.strftime("%Y-%m-%d")
            match = logs_df[
                (logs_df['Student'] == sel_name) & 
                (logs_df['Day'] == sel_day) & 
                (logs_df['Date_Only'] == today_str)
            ]
            if not match.empty:
                is_duplicate = True

        if is_duplicate:
            st.error(f"❌ ชื่อนี้วันนี้มีการลงคะแนนแล้วในช่อง {sel_day}")
            st.info("ระบบไม่อนุญาตให้บันทึกซ้ำในวันเดียวกันเพื่อป้องกันความผิดพลาด")
            can_submit = False
        else:
            can_submit = True

        if st.button("🚀 ยืนยันบันทึกคะแนน", use_container_width=True, disabled=not can_submit):
            try:
                # 1. บันทึกเจาะจงช่อง (Surgical Update) - ห้ามลบส่วนอื่น
                main_ws = sh.worksheet("Sheet1")
                row_idx = main_ws.find(sel_name, in_column=1).row
                col_idx = main_ws.find(sel_day, in_row=1).col
                
                old_val = main_ws.cell(row_idx, col_idx).value
                new_val = int(float(old_val or 0)) + pts
                main_ws.update_cell(row_idx, col_idx, new_val)
                
                # 2. บันทึกลง Logs
                log_ws.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    st.session_state.admin_name,
                    sel_name,
                    sel_day,
                    pts,
                    "Success"
                ])
                
                st.success(f"บันทึกให้ {sel_name} สำเร็จ!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- 5. หน้าบ้าน: Leaderboard (5-Column) ---
st.markdown("<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)
try:
    df_v = load_view_data()
    # ดึงคอลัมน์ A(0), AL(37), AM(38), AN(39)
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
except: st.info("กำลังโหลดข้อมูลล่าสุด...")
