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

# CSS: Super Compact
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    [data-testid="block-container"] { padding: 0.3rem 0.1rem !important; max-width: 100vw !important; overflow-x: hidden !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    * { box-sizing: border-box; }
    html, body { font-family: 'Sarabun', sans-serif; background-color: #f0f2f5; width: 100%; overflow-x: hidden; }
    .leaderboard-grid { display: grid; grid-template-columns: repeat(5, 1fr) !important; gap: 2px; width: 100%; padding: 0 1px; }
    .player-card { 
        background: white; border-radius: 3px; padding: 3px 1px 1px 1px; border: 0.5px solid #ccc; 
        display: flex; flex-direction: column; gap: 0px; min-height: 0; box-shadow: 0 1px 2px rgba(0,0,0,0.05); width: 100%; overflow: hidden;
    }
    .row-name { display: flex; align-items: center; gap: 1px; font-size: 2.2vw; font-weight: 600; color: #333; border-bottom: 0.5px solid #eee; padding-bottom: 1px; margin-bottom: 1px; white-space: nowrap; overflow: hidden; }
    .player-name-text { overflow: hidden; text-overflow: ellipsis; flex: 1; }
    .row-stat { display: flex; justify-content: space-between; align-items: center; font-size: 1.9vw; line-height: 1.0; margin-bottom: 1px; }
    .label-text { color: #888; font-size: 1.7vw; }
    .val-score { color: #1E88E5; font-weight: 800; font-size: 2.4vw; }
    .val-exp { color: #555; font-weight: 600; font-size: 2vw; }
    .row-medal { font-size: 1.8vw; color: #ef6c00; font-weight: 600; text-align: center; background: #fff3e0; border-radius: 2px; padding: 1px 0; margin-top: 1px; margin-bottom: 0px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    @media (min-width: 1024px) {
        .leaderboard-grid { gap: 10px; padding: 0 20px; }
        .player-card { padding: 8px 10px 4px 10px; min-height: 0; gap: 4px; }
        .row-name { font-size: 0.95rem; }
        .row-stat { font-size: 0.85rem; margin-bottom: 4px; }
        .val-score { font-size: 1.2rem; }
        .row-medal { font-size: 0.75rem; padding: 3px 0; margin-top: 4px; }
    }
</style>
""", unsafe_allow_html=True)

# --- 2. ฟังก์ชันจัดการข้อมูล ---
def get_monday_0600_cutoff():
    now = datetime.now(thai_tz)
    # หาวันจันทร์ที่ผ่านมา (0=จันทร์, 6=อาทิตย์)
    days_since_monday = now.weekday()
    # ปรับให้เป็นวันจันทร์สัปดาห์นี้ 06:00:00 (เป๊ะๆ)
    cutoff = (now - timedelta(days=days_since_monday)).replace(hour=6, minute=0, second=0, microsecond=0)
    
    # ถ้าตอนนี้ยังไม่ถึงวันจันทร์ 06:00 (เช่น เป็นวันอาทิตย์) ให้ถอยไปวันจันทร์ที่แล้ว
    if now < cutoff:
        cutoff -= timedelta(days=7)
    return cutoff
        
    return cutoff
@st.cache_data(ttl=None)  # เก็บไว้จนกว่า Key (update_dt) จะเปลี่ยน หรือจนกว่าจะสั่งล้าง
def load_leaderboard_daily(update_dt):
    conn = st.connection("gsheets", type=GSheetsConnection)
    # เปลี่ยน ttl เป็น None หรือค่าที่นานๆ เพื่อให้ Cache ชั้นนอกทำงาน
    df = conn.read(worksheet="Sheet1", ttl=None) 
    ld = df.iloc[:, [0, 37, 38, 39]].copy()
    ld.columns = ['Name', 'Score', 'EXP', 'Medal']
    ld['Score'] = pd.to_numeric(ld['Score'], errors='coerce').fillna(0).astype(int)
    ld['EXP'] = pd.to_numeric(ld['EXP'], errors='coerce').fillna(0).astype(int)
    ld['Rank'] = ld['Score'].rank(method='dense', ascending=False).astype(int)
    thai_date = f"{update_dt.day:02d}/{update_dt.month:02d}/{update_dt.year + 543}"
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
        if s_id and len(s_id) < 100: return client.open_by_key(s_id)
        return client.open_by_url(conf.get("url") or s_id)
    except: return None

# --- 3. ส่วนควบคุมหน้าจอ ---
if st.session_state.page == "leaderboard":
    if st.button("🔐 แอดมิน", key="login_btn"):
        st.session_state.page = "login"; st.rerun()
    
    update_dt = get_monday_0600_cutoff() # ใช้ฟังก์ชันใหม่
    players, thai_update_str = load_leaderboard_daily(update_dt)
    
    st.markdown("<h3 style='text-align: center; color: #1E88E5; margin:0;'>🏆 ทำเนียบเทพพัฒวิทย์</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; font-size: 0.7rem; color: #888; margin-bottom:5px;'>อัปเดตทุกเช้าวันจันทร์ (06:00 น.): {thai_update_str}</p>", unsafe_allow_html=True)
    
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
        st.markdown("<h4 style='text-align: center;'>🔐 Login Admin</h4>", unsafe_allow_html=True)
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
        if st.button("🏆 ดู Leaderboard", use_container_width=True): 
            st.session_state.page = "leaderboard"; st.rerun()
    with c2:
        if st.button("🚪 ออก", use_container_width=True):
            st.session_state.logged_in = False; st.query_params.clear(); st.session_state.page = "leaderboard"; st.rerun()
    
    if st.button("🔄 อัปเดตข้อมูลหน้า Leaderboard ทันที (Manual Update)", use_container_width=True):
        st.cache_data.clear()
        st.success("อัปเดตเรียบร้อย!")
        st.rerun()
  
    st.divider()
    
    df_main = load_admin_data()
    sh = get_gspread_sh()
    
    if sh:
        try: # --- TRY ใหญ่สำหรับ Google Sheets ---
            log_ws = sh.worksheet("Logs")
            logs_df = pd.DataFrame(log_ws.get_all_records())
            
            with st.container(border=True):
                st.write("🔍 **บันทึกคะแนน**")
                sc1, sc2, sc3 = st.columns([3, 1, 1])
                with sc1: input_name = st.text_input("ค้นชื่อ...", label_visibility="collapsed")
                with sc2:
                    if st.button("🔍 ค้นหา", use_container_width=True): st.session_state.search_result = input_name
                with sc3:
                    if st.button("🔄 ล้าง", use_container_width=True): st.session_state.search_result = ""; st.rerun()
                
                all_n = df_main.iloc[:, 0].dropna().tolist()
                search_term = st.session_state.search_result
                f_names = [n for n in all_n if search_term.lower() in str(n).lower()] if search_term else all_n
                sel_name = st.selectbox(f"เลือก ({len(f_names)} คน)", f_names)
                
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
                
                if is_dup: 
                    st.error("วันนี้ให้คะแนนคนนี้แล้ว")
                else:
                    if st.button("🚀 ยืนยัน", use_container_width=True):
                        try:
                            # 1. หาพิกัดแถวและคอลัมน์ (เหมือนเดิม)
                            row_idx = df_main[df_main.iloc[:,0] == sel_name].index[0] + 2
                            col_idx = df_main.columns.get_loc(sel_day) + 1
                            
                            # 2. ดึงค่าเดิมและจัดการปัญหาช่องว่าง (แก้ไขใหม่ให้หายขาด)
                            raw_val = df_main.at[row_idx-2, sel_day]
                            val_as_numeric = pd.to_numeric(raw_val, errors='coerce')
                            
                            # ถ้าเป็นค่าว่าง (NaN) ให้เป็น 0 ถ้าไม่ว่างให้แปลงเป็นจำนวนเต็ม
                            current_score = 0 if pd.isna(val_as_numeric) else int(val_as_numeric)
                            
                            # 3. อัปเดตคะแนนลง Google Sheets
                            sh.worksheet("Sheet1").update_cell(row_idx, col_idx, current_score + pts)
                            
                            # 4. บันทึกประวัติการให้คะแนน (Log)
                            log_ws.append_row([
                                datetime.now(thai_tz).strftime("%Y-%m-%d %H:%M:%S"), 
                                st.session_state.admin_name, 
                                sel_name, 
                                pts, 
                                sel_day
                            ])
                            
                            st.success(f"บันทึกให้ {sel_name} เรียบร้อยแล้ว!")
                            st.cache_data.clear() 
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
        except Exception as e: # --- EXCEPT ของ TRY ใหญ่ ---
            st.error(f"⚠️ ปัญหาการเชื่อมต่อ Sheets: {str(e)}")
