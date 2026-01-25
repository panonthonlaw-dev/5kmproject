import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pytz

# --- 1. ระบบจัดการสถานะและ Login ---
query_params = st.query_params
if "page" not in st.session_state:
    st.session_state.page = "leaderboard"
if "search_result" not in st.session_state:
    st.session_state.search_result = ""
if "logged_in" not in st.session_state:
    if query_params.get("admin_auth") == "true":
        st.session_state.logged_in = True
        st.session_state.admin_name = query_params.get("user", "")
        st.session_state.page = "admin"
    else:
        st.session_state.logged_in = False

thai_tz = pytz.timezone('Asia/Bangkok')
st.set_page_config(page_title="Patwit System 2026", layout="wide")

# CSS: ล็อก 5 คอลัมน์ และจัด 4 บรรทัด (Left-Right Alignment)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    [data-testid="block-container"] { padding: 0.5rem 0.2rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body { font-family: 'Sarabun', sans-serif; background-color: #f0f2f5; }
    .leaderboard-grid { display: grid; grid-template-columns: repeat(5, 1fr) !important; gap: 5px; }
    .player-card { 
        background: white; border-radius: 6px; padding: 6px; border: 1px solid #ddd; 
        display: flex; flex-direction: column; gap: 2px; min-height: 150px; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
    }
    .row-name { 
        display: flex; align-items: center; gap: 4px; font-size: 2.6vw; font-weight: 600; 
        color: #333; border-bottom: 1px solid #eee; padding-bottom: 2px; margin-bottom: 2px;
    }
    .player-name-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .row-stat { display: flex; justify-content: space-between; align-items: center; font-size: 2.4vw; line-height: 1.4; }
    .label-text { color: #777; font-weight: 400; }
    .val-score { color: #1E88E5; font-weight: 800; font-size: 3vw; }
    .val-exp { color: #444; font-weight: 600; }
    .row-medal { 
        font-size: 2.2vw; color: #ef6c00; font-weight: 600; text-align: center; 
        background: #fff3e0; border-radius: 4px; padding: 2px 0; margin-top: auto; 
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    @media (min-width: 1024px) {
        .player-card { padding: 12px; min-height: 180px; gap: 8px; }
        .row-name { font-size: 1.1rem; }
        .row-stat { font-size: 1rem; }
        .val-score { font-size: 1.4rem; }
        .row-medal { font-size: 0.9rem; padding: 5px 0; }
    }
</style>
""", unsafe_allow_html=True)

# --- 2. ฟังก์ชันจัดการข้อมูล (ปรับเป็นรายวัน 18:00) ---

def get_daily_1800_dt():
    """คำนวณหาเวลาอัปเดตล่าสุด (ทุกวันตอน 18:00)"""
    now = datetime.now(thai_tz)
    today_1800 = now.replace(hour=18, minute=0, second=0, microsecond=0)
    if now < today_1800:
        # ถ้ายังไม่ถึง 18:00 วันนี้ ให้ใช้ 18:00 ของเมื่อวาน
        update_time = today_1800 - timedelta(days=1)
    else:
        # ถ้าเลย 18:00 วันนี้แล้ว ให้ใช้ 18:00 ของวันนี้
        update_time = today_1800
    return update_time

@st.cache_data(ttl=None)
def load_leaderboard_daily(update_dt):
    """โหลดข้อมูลและแช่แข็งไว้จนกว่าจะถึง 18:00 ของวันถัดไป"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl="0s")
    ld = df.iloc[:, [0, 37, 38, 39]].copy()
    ld.columns = ['Name', 'Score', 'EXP', 'Medal']
    ld['Score'] = pd.to_numeric(ld['Score'], errors='coerce').fillna(0).astype(int)
    ld['EXP'] = pd.to_numeric(ld['EXP'], errors='coerce').fillna(0).astype(int)
    ld['Rank'] = ld['Score'].rank(method='dense', ascending=False).astype(int)
    thai_date = f"{update_dt.day:02d}/{update_dt.month:02d}/{update_dt.year + 543} (18:00 น.)"
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
        if s_id and len(s_id) < 100:
            return client.open_by_key(s_id)
        return client.open_by_url(conf.get("url") or s_id)
    except:
        return None

# --- 3. ส่วนควบคุมหน้าจอ ---

if st.session_state.page == "leaderboard":
    col_admin, _ = st.columns([1, 8])
    with col_admin:
        if st.button("🔐 แอดมิน", key="login_btn"):
            st.session_state.page = "login"
            st.rerun()
    
    # ดึงเวลาตัดรอบ 18:00 และโหลดข้อมูล
    update_dt = get_daily_1800_dt()
    players, thai_update_str = load_leaderboard_daily(update_dt)
    
    st.markdown("<h3 style='text-align: center; color: #1E88E5; margin:0;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; font-size: 0.8rem; color: #888; margin-bottom:10px;'>อัปเดตคะแนนล่าสุดเมื่อ: {thai_update_str}</p>", unsafe_allow_html=True)
    
    # สร้าง Grid (เขียน HTML แบบไม่มีเว้นวรรคเยอะ ป้องกันหน้าจอแสดงผลเป็นโค้ด)
    grid_h = '<div class="leaderboard-grid">'
    for p in players:
        icon = "👑" if p['Rank'] == 1 else "🎖️"
        medal_name = str(p['Medal']) if p['Medal'] else "-"
        grid_h += (
            f'<div class="player-card">'
            f'<div class="row-name"><span>#{p["Rank"]}</span><span>{icon}</span><span class="player-name-text">{p["Name"]}</span></div>'
            f'<div class="row-stat"><span class="label-text">คะแนน</span><span class="val-score">{p["Score"]}</span></div>'
            f'<div class="row-stat"><span class="label-text">EXP</span><span class="val-exp">{p["EXP"]}</span></div>'
            f'<div class="row-medal">{medal_name}</div>'
            f'</div>'
        )
    grid_h += '</div>'
    st.markdown(grid_h, unsafe_allow_html=True)

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
                    st.query_params["admin_auth"] = "true"
                    st.query_params["user"] = u
                    st.rerun()
                else: st.error("ข้อมูลไม่ถูกต้อง")
        if st.button("⬅️ กลับหน้าหลัก"):
            st.session_state.page = "leaderboard"
            st.rerun()

elif st.session_state.page == "admin":
    if not st.session_state.logged_in:
        st.session_state.page = "login"
        st.rerun()
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏆 ดูหน้า Leaderboard", use_container_width=True):
            st.session_state.page = "leaderboard"
            st.rerun()
    with c2:
        if st.button("🚪 ออกจากระบบ", use_container_width=True):
            st.session_state.logged_in = False
            st.query_params.clear()
            st.session_state.page = "leaderboard"
            st.rerun()

    st.divider()
    df_main = load_admin_data()
    sh = get_gspread_sh()
    
    if sh:
        try:
            log_ws = sh.worksheet("Logs")
            logs_df = pd.DataFrame(log_ws.get_all_records())
            with st.container(border=True):
                st.write("🔍 **บันทึกคะแนนนักเรียน**")
                sc1, sc2, sc3 = st.columns([3, 1, 1])
                with sc1:
                    input_name = st.text_input("พิมพ์ชื่อ", label_visibility="collapsed", placeholder="ค้นหาชื่อ...")
                with sc2:
                    if st.button("🔍 ค้นหา", use_container_width=True):
                        st.session_state.search_result = input_name
                with sc3:
                    if st.button("🔄 ล้าง", use_container_width=True):
                        st.session_state.search_result = ""
                        st.rerun()

                all_n = df_main.iloc[:, 0].dropna().tolist()
                search_term = st.session_state.search_result
                f_names = [n for n in all_n if search_term.lower() in str(n).lower()] if search_term else all_n
                sel_name = st.selectbox(f"เลือกนักเรียน ({len(f_names)} คน)", f_names)
                
                days = [c for c in df_main.columns if "day" in str(c).lower()]
                d_col, p_col = st.columns(2)
                with d_col: sel_day = st.selectbox("กิจกรรม (Day)", days)
                with p_col: pts = st.number_input("คะแนน", min_value=1, value=5)

                today = datetime.now(thai_tz).strftime("%Y-%m-%d")
                is_dup = False
                if not logs_df.empty:
                    logs_df['DateOnly'] = pd.to_datetime(logs_df['Timestamp']).dt.strftime("%Y-%m-%d")
                    match = logs_df[(logs_df['Student'] == sel_name) & (logs_df['Day'] == sel_day) & (logs_df['DateOnly'] == today)]
                    if not match.empty: is_dup = True

                if is_dup: st.error(f"❌ วันนี้บันทึกช่อง '{sel_day}' ให้ '{sel_name}' ไปแล้ว!")
                else:
                    if st.button("🚀 ยืนยันบันทึกคะแนน", use_container_width=True):
                        try:
                            row_idx = df_main[df_main.iloc[:,0] == sel_name].index[0] + 2
                            col_idx = df_main.columns.get_loc(sel_day) + 1
                            raw_val = df_main.at[row_idx-2, sel_day]
                            current_score = int(pd.to_numeric(raw_val, errors='coerce') or 0)
                            sh.worksheet("Sheet1").update_cell(row_idx, col_idx, current_score + pts)
                            log_ws.append_row([datetime.now(thai_tz).strftime("%Y-%m-%d %H:%M:%S"), st.session_state.admin_name, sel_name, pts, sel_day])
                            st.success("บันทึกสำเร็จ!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
        except Exception as e: st.error(f"⚠️ ปัญหาใน Google Sheets: {str(e)}")
