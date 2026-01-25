import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

# --- 1. ระบบรักษาการ Login (Persistent Login) ---
query_params = st.query_params
if "logged_in" not in st.session_state:
    if query_params.get("admin_auth") == "true":
        st.session_state.logged_in = True
        st.session_state.admin_name = query_params.get("user", "")
    else:
        st.session_state.logged_in = False

if "show_login" not in st.session_state: st.session_state.show_login = False

thai_tz = pytz.timezone('Asia/Bangkok')
st.set_page_config(page_title="Patwit System Turbo", layout="wide")

# CSS: ล็อก 5 คอลัมน์ / ปรับแต่ง UI
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    [data-testid="block-container"] { padding: 0.5rem 0.5rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body { font-family: 'Sarabun', sans-serif; background-color: #f8f9fa; }
    .leaderboard-grid { display: grid; grid-template-columns: repeat(5, 1fr) !important; gap: 4px; }
    .player-card { background: white; border-radius: 6px; padding: 8px 3px; text-align: center; border: 1px solid #eee; display: flex; flex-direction: column; justify-content: space-between; height: 180px; }
    .player-name { font-size: 2.5vw !important; font-weight: 600; line-height: 1.1; height: 5.5vw; overflow: hidden; margin: 4px 0; }
    .score-num { font-size: 5vw !important; font-weight: 800; color: #1E88E5; line-height: 1; }
    .rank-tag { font-size: 2vw; font-weight: 600; opacity: 0.6; }
    .c-1 { color: #FFD700; } .c-2 { color: #999; } .c-3 { color: #CD7F32; }
    @media (min-width: 1024px) {
        .player-card { padding: 15px; } .player-name { font-size: 1.1rem !important; height: 45px; } .score-num { font-size: 2.2rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันการเชื่อมต่อ ---
@st.cache_resource
def get_gspread_client():
    conf = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(conf, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(worksheet="Sheet1", ttl="0s")

# ฟังก์ชันเปิดไฟล์แบบฉลาด (ป้องกัน SpreadsheetNotFound)
def open_spreadsheet(client):
    conf = st.secrets["connections"]["gsheets"]
    # ลองหาจาก ID ก่อน ถ้าไม่ได้ให้ลองหาจาก URL
    s_id = conf.get("spreadsheet")
    s_url = conf.get("url")
    
    try:
        if s_id and len(s_id) < 60: # ตรวจสอบว่าเป็น ID หรือไม่
            return client.open_by_key(s_id)
        else:
            return client.open_by_url(s_url or s_id)
    except Exception as e:
        st.error("❌ หาไฟล์ไม่เจอ: ตรวจสอบว่าแชร์สิทธิ์ให้ Service Account หรือยัง และเช็ก ID ใน Secrets ให้ถูกต้อง")
        return None

# --- 3. ส่วน Login มุมซ้ายบน ---
t_l, t_m, t_r = st.columns([1, 1, 2])
with t_l:
    if not st.session_state.logged_in:
        if st.button("🔓 แอดมิน"):
            st.session_state.show_login = not st.session_state.show_login
        if st.session_state.show_login:
            with st.form("top_login"):
                u = st.text_input("ID", label_visibility="collapsed", placeholder="ID")
                p = st.text_input("Pass", type="password", label_visibility="collapsed", placeholder="Pass")
                if st.form_submit_button("Log In"):
                    if u in st.secrets["users"] and p == st.secrets["users"][u]:
                        st.session_state.logged_in = True
                        st.session_state.admin_name = u
                        st.query_params["admin_auth"] = "true"; st.query_params["user"] = u
                        st.rerun()
                    else: st.error("ข้อมูลไม่ถูกต้อง")
    else:
        st.write(f"🛡️ **{st.session_state.admin_name}**")
        if st.button("🚪 ออก"):
            st.session_state.logged_in = False
            st.query_params.clear()
            st.rerun()

# --- 4. การแสดงผล ---
if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)
    try:
        df_v = load_data()
        ld = df_v.iloc[:, [0, 37, 38, 39]].copy()
        ld.columns = ['Name', 'Score', 'EXP', 'Medal']
        ld['Score'] = pd.to_numeric(ld['Score'], errors='coerce').fillna(0).astype(int)
        ld['Rank'] = ld['Score'].rank(method='dense', ascending=False).astype(int)
        grid_h = '<div class="leaderboard-grid">'
        for p in ld.sort_values(by=['Rank', 'Name']).to_dict('records'):
            r, icon = p['Rank'], ("👑" if p['Rank'] <= 3 else "🎖️")
            color = f"c-{r}" if r <= 3 else ""
            grid_h += f'<div class="player-card"><div class="rank-tag {color}">{icon} #{r}</div><div class="player-name">{p["Name"]}</div><div class="score-num">{p["Score"]}</div><div style="font-size:1.5vw; opacity:0.5;">คะแนนรวม</div></div>'
        st.markdown(grid_h + '</div>', unsafe_allow_html=True)
    except: st.info("กำลังโหลดข้อมูล...")

else:
    # --- หน้า Admin (Turbo Update) ---
    st.markdown("### 🎯 บันทึกคะแนนนักเรียน")
    df_main = load_data()
    
    with st.container(border=True):
        search = st.text_input("🔍 ค้นหาชื่อ", placeholder="พิมพ์เพื่อกรองรายชื่อ...")
        all_n = df_main.iloc[:, 0].dropna().tolist()
        f_names = [n for n in all_n if search.lower() in n.lower()] if search else all_n
        sel_name = st.selectbox(f"เลือกนักเรียน ({len(f_names)} คน)", f_names)
        days = [c for c in df_main.columns if "day" in str(c).lower()]
        sel_day = st.selectbox("เลือกกิจกรรม (Day)", days)
        pts = st.number_input("คะแนนที่เพิ่ม", min_value=1, value=5, step=1)

        # --- เปิดไฟล์ผ่านระบบตรวจสอบสิทธิ์ ---
        client = get_gspread_client()
        sh = open_spreadsheet(client)
        
        if sh:
            log_ws = sh.worksheet("Logs")
            logs_df = pd.DataFrame(log_ws.get_all_records())
            
            today_str = datetime.now(thai_tz).strftime("%Y-%m-%d")
            is_duplicate = False
            if not logs_df.empty:
                logs_df['DateOnly'] = pd.to_datetime(logs_df['Timestamp']).dt.strftime("%Y-%m-%d")
                match = logs_df[(logs_df['Student'] == sel_name) & (logs_df['Day'] == sel_day) & (logs_df['DateOnly'] == today_str)]
                if not match.empty: is_duplicate = True

            if is_duplicate:
                st.error(f"❌ วันนี้บันทึกช่อง '{sel_day}' ให้ '{sel_name}' ไปแล้ว!")
                can_save = False
            else: can_save = True

            if st.button("🚀 ยืนยันบันทึกคะแนน", use_container_width=True, disabled=not can_save):
                with st.spinner("กำลังบันทึก..."):
                    try:
                        # หาพิกัด
                        row_idx = df_main[df_main.iloc[:,0] == sel_name].index[0] + 2
                        col_idx = df_main.columns.get_loc(sel_day) + 1
                        old_v = df_main.at[row_idx-2, sel_day]
                        new_v = int(pd.to_numeric(old_v, errors='coerce') or 0) + pts
                        
                        # บันทึก
                        sh.worksheet("Sheet1").update_cell(row_idx, col_idx, new_v)
                        log_ws.append_row([
                            datetime.now(thai_tz).strftime("%Y-%m-%d %H:%M:%S"), 
                            st.session_state.admin_name, sel_name, pts, sel_day
                        ])
                        
                        st.success("บันทึกสำเร็จ!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e: st.error(f"เกิดข้อผิดพลาด: {e}")

            if not logs_df.empty:
                st.markdown("---")
                st.markdown("📜 **ประวัติ 5 รายการล่าสุด**")
                st.table(logs_df.tail(5)[['Timestamp', 'Student', 'Day', 'Points']])
