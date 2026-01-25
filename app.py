import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

# --- 1. ระบบรักษาการ Login (Persistent) ---
query_params = st.query_params
if "page" not in st.session_state: st.session_state.page = "leaderboard"
if "logged_in" not in st.session_state:
    if query_params.get("admin_auth") == "true":
        st.session_state.logged_in = True
        st.session_state.admin_name = query_params.get("user", "")
        st.session_state.page = "admin"
    else: st.session_state.logged_in = False

thai_tz = pytz.timezone('Asia/Bangkok')
st.set_page_config(page_title="Patwit System Turbo", layout="wide")

# CSS: ล็อก 5 คอลัมน์ / ปรับแต่ง UI
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    [data-testid="block-container"] { padding: 1rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body { font-family: 'Sarabun', sans-serif; background-color: #f8f9fa; }
    .leaderboard-grid { display: grid; grid-template-columns: repeat(5, 1fr) !important; gap: 4px; }
    .player-card { background: white; border-radius: 8px; padding: 10px 5px; text-align: center; border: 1px solid #eee; height: 180px; display: flex; flex-direction: column; justify-content: space-between; }
    .player-name { font-size: 2.5vw !important; font-weight: 600; line-height: 1.1; height: 5.5vw; overflow: hidden; }
    .score-num { font-size: 5vw !important; font-weight: 800; color: #1E88E5; }
    .rank-tag { font-size: 2vw; font-weight: 600; opacity: 0.6; }
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

# ฟังก์ชันเปิดไฟล์แบบ Safe-Mode
def open_sh(client):
    conf = st.secrets["connections"]["gsheets"]
    s_id = conf.get("spreadsheet")
    s_url = conf.get("url")
    try:
        # ถ้าเป็นรหัสยาวๆ ให้เปิดด้วย key ถ้าเป็นลิงก์ให้เปิดด้วย URL
        if s_id and "docs.google.com" not in s_id:
            return client.open_by_key(s_id)
        return client.open_by_url(s_url or s_id)
    except Exception as e:
        st.error("❌ หาไฟล์ Google Sheets ไม่เจอ! ตรวจสอบว่าแชร์สิทธิ์ Editor ให้ Service Account หรือยัง?")
        return None

# --- 3. ส่วนควบคุมหน้าจอ ---

if st.session_state.page == "leaderboard":
    if st.button("🔐 สำหรับแอดมิน"):
        st.session_state.page = "login"
        st.rerun()
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
            grid_h += f'<div class="player-card"><div><div class="rank-tag">#{r} {icon}</div><div class="player-name">{p["Name"]}</div></div><div class="score-num">{p["Score"]}</div><div style="font-size:1.5vw; opacity:0.5;">คะแนน</div></div>'
        st.markdown(grid_h + '</div>', unsafe_allow_html=True)
    except: st.info("กำลังโหลด...")

elif st.session_state.page == "login":
    _, center_col, _ = st.columns([1, 1, 1])
    with center_col:
        st.markdown("<h2 style='text-align: center;'>🔐 Login Admin</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("ID")
            p = st.text_input("Pass", type="password")
            if st.form_submit_button("เข้าสู่ระบบ", use_container_width=True):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state.logged_in = True
                    st.session_state.admin_name = u
                    st.session_state.page = "admin"
                    st.query_params["admin_auth"] = "true"; st.query_params["user"] = u
                    st.rerun()
                else: st.error("ข้อมูลไม่ถูกต้อง")
        if st.button("⬅️ กลับหน้าหลัก"):
            st.session_state.page = "leaderboard"
            st.rerun()

elif st.session_state.page == "admin":
    if not st.session_state.logged_in:
        st.session_state.page = "login"
        st.rerun()
    
    # ส่วนหัว Admin
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏆 ดูหน้า Leaderboard", use_container_width=True):
            st.session_state.page = "leaderboard"; st.rerun()
    with c2:
        if st.button("🚪 ออกจากระบบ", use_container_width=True):
            st.session_state.logged_in = False; st.query_params.clear()
            st.session_state.page = "leaderboard"; st.rerun()

    st.divider()
    
    # ระบบบันทึกคะแนน
    df_main = load_data()
    sh_client = get_gspread_client()
    sh = open_sh(sh_client)
    
    if sh:
        with st.container(border=True):
            search = st.text_input("🔍 ค้นชื่อนักเรียน")
            all_n = df_main.iloc[:, 0].dropna().tolist()
            f_names = [n for n in all_n if search.lower() in n.lower()] if search else all_n
            sel_name = st.selectbox(f"เลือกนักเรียน ({len(f_names)} คน)", f_names)
            days = [c for c in df_main.columns if "day" in str(c).lower()]
            sel_day = st.selectbox("กิจกรรม (Day)", days)
            pts = st.number_input("คะแนน", min_value=1, value=5)

            # เช็กซ้ำ
            log_ws = sh.worksheet("Logs")
            logs_df = pd.DataFrame(log_ws.get_all_records())
            today = datetime.now(thai_tz).strftime("%Y-%m-%d")
            
            is_dup = False
            if not logs_df.empty:
                logs_df['DateOnly'] = pd.to_datetime(logs_df['Timestamp']).dt.strftime("%Y-%m-%d")
                match = logs_df[(logs_df['Student'] == sel_name) & (logs_df['Day'] == sel_day) & (logs_df['DateOnly'] == today)]
                if not match.empty: is_dup = True

            if is_dup:
                st.error(f"❌ วันนี้ลงคะแนนช่อง '{sel_day}' ให้ '{sel_name}' ไปแล้ว!")
            else:
                if st.button("🚀 ยืนยันบันทึกคะแนน", use_container_width=True):
                    with st.spinner("กำลังบันทึก..."):
                        try:
                            row_idx = df_main[df_main.iloc[:,0] == sel_name].index[0] + 2
                            col_idx = df_main.columns.get_loc(sel_day) + 1
                            old_v = df_main.at[row_idx-2, sel_day]
                            new_v = int(pd.to_numeric(old_v, errors='coerce') or 0) + pts
                            
                            sh.worksheet("Sheet1").update_cell(row_idx, col_idx, new_v)
                            log_ws.append_row([datetime.now(thai_tz).strftime("%Y-%m-%d %H:%M:%S"), st.session_state.admin_name, sel_name, pts, sel_day])
                            st.success("บันทึกสำเร็จ!")
                            st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

        if not logs_df.empty:
            st.table(logs_df.tail(5)[['Timestamp', 'Student', 'Day', 'Points']])
