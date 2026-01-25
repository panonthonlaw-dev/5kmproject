import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pytz

# --- 1. ระบบจัดการหน้าจอและสถานะ ---
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
st.set_page_config(page_title="Patwit System 2026", layout="wide")

# CSS: ปรับปรุงการแสดงผล 5 คอลัมน์ ไม่ให้ข้อมูลตกขอบ
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    [data-testid="block-container"] { padding: 0.8rem 0.2rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body { font-family: 'Sarabun', sans-serif; background-color: #f8f9fa; }
    
    /* Grid 5 คอลัมน์ */
    .leaderboard-grid { 
        display: grid; 
        grid-template-columns: repeat(5, 1fr) !important; 
        gap: 6px; 
    }
    
    /* การ์ดผู้เล่น: ปรับให้รองรับเนื้อหา EXP และฉายา */
    .player-card { 
        background: white; 
        border-radius: 8px; 
        padding: 8px 4px; 
        text-align: center; 
        border: 1px solid #eee; 
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
        min-height: 220px; /* เพิ่มความสูงขั้นต่ำป้องกันตกขอบ */
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .rank-tag { font-size: 2.2vw !important; font-weight: 600; color: #666; margin-bottom: 2px; }
    .player-name { 
        font-size: 2.6vw !important; 
        font-weight: 600; 
        color: #333; 
        line-height: 1.1; 
        height: 5.8vw; 
        display: -webkit-box; 
        -webkit-line-clamp: 2; 
        -webkit-box-orient: vertical; 
        overflow: hidden; 
        margin: 5px 0;
    }
    .score-num { font-size: 5.5vw !important; font-weight: 800; color: #1E88E5; line-height: 1; }
    
    /* ส่วนข้อมูลด้านล่าง (EXP/ฉายา) */
    .info-box {
        border-top: 1px solid #f0f0f0;
        padding-top: 6px;
        margin-top: 4px;
        text-align: left;
    }
    .info-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px; }
    .info-label { font-size: 1.8vw !important; color: #888; }
    .info-val { font-size: 2vw !important; font-weight: 600; color: #444; }
    
    @media (min-width: 1024px) {
        .player-card { padding: 15px; min-height: 250px; }
        .player-name { font-size: 1.1rem !important; height: 45px; }
        .score-num { font-size: 2.5rem !important; }
        .rank-tag { font-size: 0.9rem !important; }
        .info-label { font-size: 0.75rem !important; }
        .info-val { font-size: 0.85rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันจัดการข้อมูล ---

def get_weekly_monday_dt():
    now = datetime.now(thai_tz)
    days_since_monday = now.weekday()
    last_monday = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=1, second=0, microsecond=0)
    if now < last_monday:
        last_monday -= timedelta(days=7)
    return last_monday

@st.cache_data(ttl=None)
def load_leaderboard_weekly(monday_dt):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl="0s")
    # ดึง Name(0), Score(37), EXP(38), Medal(39)
    ld = df.iloc[:, [0, 37, 38, 39]].copy()
    ld.columns = ['Name', 'Score', 'EXP', 'Medal']
    ld['Score'] = pd.to_numeric(ld['Score'], errors='coerce').fillna(0).astype(int)
    ld['EXP'] = pd.to_numeric(ld['EXP'], errors='coerce').fillna(0).astype(int)
    ld['Rank'] = ld['Score'].rank(method='dense', ascending=False).astype(int)
    
    thai_date = f"{monday_dt.day:02d}/{monday_dt.month:02d}/{monday_dt.year + 543}"
    return ld.sort_values(by=['Rank', 'Name']).to_dict('records'), thai_date

def load_admin_data():
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
    if st.button("🔐 แอดมิน"):
        st.session_state.page = "login"; st.rerun()
    
    monday_dt = get_weekly_monday_dt()
    players, thai_date_str = load_leaderboard_weekly(monday_dt)
    
    st.markdown(f"<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า (ประจำสัปดาห์)</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; font-size: 0.9rem; color: #888;'>อัปเดตล่าสุด: {thai_date_str}</p>", unsafe_allow_html=True)
    
    grid_h = '<div class="leaderboard-grid">'
    for p in players:
        icon = "👑" if p['Rank'] == 1 else "🎖️"
        # จัดการชื่อฉายาให้ขึ้นบรรทัดใหม่ได้ถ้าจำเป็น
        medal_text = str(p['Medal']) if p['Medal'] else "-"
        
        grid_h += f"""
        <div class="player-card">
            <div>
                <div class="rank-tag">#{p['Rank']} {icon}</div>
                <div class="player-name">{p['Name']}</div>
            </div>
            <div>
                <div class="score-num">{p['Score']}</div>
                <div style="font-size: 1.8vw; color: #999; margin-bottom: 5px;">คะแนนรวม</div>
            </div>
            <div class="info-box">
                <div class="info-row">
                    <span class="info-label">EXP:</span>
                    <span class="info-val">{p['EXP']}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">ฉายา:</span>
                    <span class="info-val" style="font-size: 1.8vw !important;">{medal_text}</span>
                </div>
            </div>
        </div>
        """
    st.markdown(grid_h + '</div>', unsafe_allow_html=True)

# (ส่วน Login และ Admin ทำงานเหมือนเดิม)
elif st.session_state.page == "login":
    _, center_col, _ = st.columns([1, 1, 1])
    with center_col:
        st.markdown("<h2 style='text-align: center;'>🔐 Login</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            u, p = st.text_input("ID"), st.text_input("Pass", type="password")
            if st.form_submit_button("เข้าสู่ระบบ", use_container_width=True):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state.logged_in = True; st.session_state.admin_name = u
                    st.session_state.page = "admin"; st.query_params["admin_auth"] = "true"; st.query_params["user"] = u
                    st.rerun()
                else: st.error("ข้อมูลไม่ถูกต้อง")
        if st.button("⬅️ กลับ"): st.session_state.page = "leaderboard"; st.rerun()

elif st.session_state.page == "admin":
    if not st.session_state.logged_in: st.session_state.page = "login"; st.rerun()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏆 ดูหน้าหลัก", use_container_width=True): st.session_state.page = "leaderboard"; st.rerun()
    with c2:
        if st.button("🚪 ออกจากระบบ", use_container_width=True):
            st.session_state.logged_in = False; st.query_params.clear(); st.session_state.page = "leaderboard"; st.rerun()
    st.divider()
    df_main = load_admin_data()
    sh = get_gspread_sh()
    if sh:
        log_ws = sh.worksheet("Logs")
        logs_df = pd.DataFrame(log_ws.get_all_records())
        with st.container(border=True):
            st.write("🔍 **บันทึกคะแนน**")
            sc1, sc2, sc3 = st.columns([3, 1, 1])
            with sc1: input_name = st.text_input("พิมพ์ชื่อ", placeholder="ค้นหา...")
            with sc2:
                if st.button("🔍 ค้นหา", use_container_width=True): st.session_state.search_result = input_name
            with sc3:
                if st.button("🔄 ล้าง", use_container_width=True): st.session_state.search_result = ""; st.rerun()
            all_n = df_main.iloc[:, 0].dropna().tolist()
            search_term = st.session_state.search_result
            f_names = [n for n in all_n if search_term.lower() in str(n).lower()] if search_term else all_n
            sel_name = st.selectbox(f"นักเรียน ({len(f_names)} คน)", f_names)
            days = [c for c in df_main.columns if "day" in str(c).lower()]
            d_col, p_col = st.columns(2)
            with d_col: sel_day = st.selectbox("กิจกรรม", days)
            with p_col: pts = st.number_input("คะแนน", min_value=1, value=5)
            today = datetime.now(thai_tz).strftime("%Y-%m-%d")
            is_dup = False
            if not logs_df.empty:
                logs_df['DateOnly'] = pd.to_datetime(logs_df['Timestamp']).dt.strftime("%Y-%m-%d")
                match = logs_df[(logs_df['Student'] == sel_name) & (logs_df['Day'] == sel_day) & (logs_df['DateOnly'] == today)]
                if not match.empty: is_dup = True
            if is_dup: st.error("❌ บันทึกซ้ำไม่ได้!")
            else:
                if st.button("🚀 ยืนยัน", use_container_width=True):
                    try:
                        row_idx = df_main[df_main.iloc[:,0] == sel_name].index[0] + 2
                        col_idx = df_main.columns.get_loc(sel_day) + 1
                        old_v = int(pd.to_numeric(df_main.at[row_idx-2, sel_day], errors='coerce') or 0)
                        sh.worksheet("Sheet1").update_cell(row_idx, col_idx, old_v + pts)
                        log_ws.append_row([datetime.now(thai_tz).strftime("%Y-%m-%d %H:%M:%S"), st.session_state.admin_name, sel_name, pts, sel_day])
                        st.success("บันทึกสำเร็จ!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
