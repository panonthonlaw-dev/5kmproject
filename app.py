import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pytz

# --- 1. ระบบรักษาการ Login (Refresh ไม่หลุด) ---
query_params = st.query_params
if "page" not in st.session_state: st.session_state.page = "leaderboard"
if "search_result" not in st.session_state: st.session_state.search_result = ""

if "logged_in" not in st.session_state:
    if query_params.get("admin_auth") == "true":
        st.session_state.logged_in = True
        st.session_state.admin_name = query_params.get("user", "")
        st.session_state.page = "admin"
    else: st.session_state.logged_in = False

thai_tz = pytz.timezone('Asia/Bangkok')
st.set_page_config(page_title="Patwit Weekly System", layout="wide")

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

# --- 2. ฟังก์ชันการดึงข้อมูล (แบบ Weekly Cache) ---

def get_weekly_key():
    """คำนวณกุญแจสำหรับล็อคข้อมูลรายสัปดาห์ (จันทร์ 00:01)"""
    now = datetime.now(thai_tz)
    # หาวันจันทร์ล่าสุด
    days_since_monday = now.weekday()
    last_monday = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=1, second=0, microsecond=0)
    # ถ้าตอนนี้ยังไม่ถึงจันทร์ 00:01 ของสัปดาห์นี้ ให้ย้อนไปจันทร์ที่แล้ว
    if now < last_monday:
        last_monday -= timedelta(days=7)
    return last_monday.strftime("%Y-Week%W-%d")

@st.cache_data(ttl=None) # ใช้ระบบแคชแบบไม่มีวันหมดอายุ จนกว่า Key จะเปลี่ยน
def load_leaderboard_weekly(version_key):
    """ดึงข้อมูล Leaderboard และแช่แข็งไว้จนกว่าจะถึงจันทร์หน้า"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl="0s")
    # ดึง Name(0), Score(37), EXP(38), Medal(39)
    ld = df.iloc[:, [0, 37, 38, 39]].copy()
    ld.columns = ['Name', 'Score', 'EXP', 'Medal']
    ld['Score'] = pd.to_numeric(ld['Score'], errors='coerce').fillna(0).astype(int)
    ld['Rank'] = ld['Score'].rank(method='dense', ascending=False).astype(int)
    return ld.sort_values(by=['Rank', 'Name']).to_dict('records'), last_monday_display(version_key)

def last_monday_display(v_key):
    return v_key

def load_admin_data():
    """ข้อมูลหน้า Admin ต้อง Real-time เสมอเพื่อเช็กคะแนนล่าสุด"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(worksheet="Sheet1", ttl="0s")

def get_gspread_sh():
    try:
        conf = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(conf, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        client = gspread.authorize(creds)
        s_id = conf.get("spreadsheet")
        return client.open_by_key(s_id) if s_id and len(s_id) < 100 else client.open_by_url(conf.get("url") or s_id)
    except: return None

# --- 3. ส่วนควบคุมหน้าจอ ---

if st.session_state.page == "leaderboard":
    # ปุ่ม Login มุมซ้ายบน
    if st.button("🔐 สำหรับแอดมิน"):
        st.session_state.page = "login"; st.rerun()
    
    # คำนวณเวอร์ชั่นสัปดาห์
    v_key = get_weekly_key()
    players, update_info = load_leaderboard_weekly(v_key)
    
    st.markdown(f"<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า (ประจำสัปดาห์)</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; font-size: 0.8rem; color: #888;'>อัปเดตล่าสุด: {update_info}</p>", unsafe_allow_html=True)
    
    grid_h = '<div class="leaderboard-grid">'
    for p in players:
        r, icon = p['Rank'], ("👑" if p['Rank'] <= 3 else "🎖️")
        grid_h += f'<div class="player-card"><div><div class="rank-tag">#{r} {icon}</div><div class="player-name">{p["Name"]}</div></div><div class="score-num">{p["Score"]}</div><div style="font-size:1.5vw; opacity:0.5;">คะแนน</div></div>'
    st.markdown(grid_h + '</div>', unsafe_allow_html=True)

elif st.session_state.page == "login":
    _, center_col, _ = st.columns([1, 1, 1])
    with center_col:
        st.markdown("<h2 style='text-align: center;'>🔐 Login Admin</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            u, p = st.text_input("ID"), st.text_input("Pass", type="password")
            if st.form_submit_button("เข้าสู่ระบบ", use_container_width=True):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state.logged_in = True; st.session_state.admin_name = u
                    st.session_state.page = "admin"; st.query_params["admin_auth"] = "true"; st.query_params["user"] = u
                    st.rerun()
                else: st.error("ข้อมูลไม่ถูกต้อง")
        if st.button("⬅️ กลับหน้าหลัก"): st.session_state.page = "leaderboard"; st.rerun()

elif st.session_state.page == "admin":
    if not st.session_state.logged_in: st.session_state.page = "login"; st.rerun()
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏆 ดูหน้า Leaderboard", use_container_width=True): st.session_state.page = "leaderboard"; st.rerun()
    with c2:
        if st.button("🚪 ออกจากระบบ", use_container_width=True):
            st.session_state.logged_in = False; st.query_params.clear(); st.session_state.page = "leaderboard"; st.rerun()

    st.divider()
    
    # ระบบบันทึกคะแนน (หน้า Admin ต้องเห็นข้อมูลจริงล่าสุดเสมอ)
    df_main = load_admin_data()
    sh = get_gspread_sh()
    
    if sh:
        log_ws = sh.worksheet("Logs")
        logs_df = pd.DataFrame(log_ws.get_all_records())
        
        with st.container(border=True):
            st.write("🔍 **ค้นหาและบันทึกคะแนน**")
            sc1, sc2, sc3 = st.columns([3, 1, 1])
            with sc1: input_name = st.text_input("พิมพ์ชื่อ", label_visibility="collapsed", placeholder="พิมพ์ชื่อนักเรียน...")
            with sc2:
                if st.button("🔍 ค้นหา", use_container_width=True): st.session_state.search_result = input_name
            with sc3:
                if st.button("🔄 ล้าง", use_container_width=True): st.session_state.search_result = ""; st.rerun()

            all_n = df_main.iloc[:, 0].dropna().tolist()
            search_term = st.session_state.search_result
            f_names = [n for n in all_n if search_term.lower() in str(n).lower()] if search_term else all_n
            sel_name = st.selectbox(f"เลือกนักเรียน ({len(f_names)} คน)", f_names)
            
            days = [c for c in df_main.columns if "day" in str(c).lower()]
            d_col, p_col = st.columns(2)
            with d_col: sel_day = st.selectbox("กิจกรรม (Day)", days)
            with p_col: pts = st.number_input("คะแนน", min_value=1, value=5)

            # เช็กซ้ำ (รายวัน)
            today = datetime.now(thai_tz).strftime("%Y-%m-%d")
            is_dup = False
            if not logs_df.empty:
                logs_df['DateOnly'] = pd.to_datetime(logs_df['Timestamp']).dt.strftime("%Y-%m-%d")
                match = logs_df[(logs_df['Student'] == sel_name) & (logs_df['Day'] == sel_day) & (logs_df['DateOnly'] == today)]
                if not match.empty: is_dup = True

            if is_dup:
                st.error(f"❌ วันนี้บันทึกช่อง '{sel_day}' ให้ '{sel_name}' ไปแล้ว!")
            else:
                if st.button("🚀 ยืนยันบันทึกคะแนน", use_container_width=True):
                    with st.spinner("กำลังบันทึก..."):
                        try:
                            row_idx = df_main[df_main.iloc[:,0] == sel_name].index[0] + 2
                            col_idx = df_main.columns.get_loc(sel_day) + 1
                            raw_val = df_main.at[row_idx-2, sel_day]
                            current_score = int(pd.to_numeric(raw_val, errors='coerce') or 0)
                            
                            sh.worksheet("Sheet1").update_cell(row_idx, col_idx, current_score + pts)
                            log_ws.append_row([datetime.now(thai_tz).strftime("%Y-%m-%d %H:%M:%S"), st.session_state.admin_name, sel_name, pts, sel_day])
                            st.success("บันทึกสำเร็จ! (อันดับในหน้า Leaderboard จะอัปเดตวันจันทร์หน้า)")
                            st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"เกิดข้อผิดพลาด: {e}")

        if not logs_df.empty: st.table(logs_df.tail(3)[['Timestamp', 'Student', 'Day', 'Points']])
