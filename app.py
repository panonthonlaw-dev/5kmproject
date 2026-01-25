import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. ตั้งค่าพื้นฐานป้องกัน Error ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "admin_name" not in st.session_state: st.session_state.admin_name = ""
if "show_login" not in st.session_state: st.session_state.show_login = False

st.set_page_config(page_title="Patwit System", layout="wide")

# CSS จัดหน้าจอและ Leaderboard 5 คอลัมน์
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    [data-testid="block-container"] { padding: 0.5rem 0.5rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body { font-family: 'Sarabun', sans-serif; background-color: #f8f9fa; }
    .leaderboard-grid { display: grid; grid-template-columns: repeat(5, 1fr) !important; gap: 4px; }
    .player-card { background: white; border-radius: 6px; padding: 8px 3px; text-align: center; border: 1px solid #eee; }
    .player-name { font-size: 2.5vw !important; font-weight: 600; line-height: 1.1; height: 5.5vw; overflow: hidden; }
    .score-num { font-size: 5vw !important; font-weight: 800; color: #1E88E5; }
    .rank-tag { font-size: 2vw; font-weight: 600; opacity: 0.6; }
    .c-1 { color: #FFD700; } .c-2 { color: #999; } .c-3 { color: #CD7F32; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. การเชื่อมต่อข้อมูล ---
def get_sh():
    conf = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(conf, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    s_id = conf.get("spreadsheet") or conf.get("url")
    return client.open_by_key(s_id) if len(s_id) < 60 else client.open_by_url(s_id)

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(worksheet="Sheet1", ttl="0s")

# --- 3. ส่วน Login (มุมซ้ายบน) ---
t_l, t_m, t_r = st.columns([1, 1, 2])
with t_l:
    if not st.session_state.logged_in:
        if st.button("🔓 แอดมินล็อกอิน"):
            st.session_state.show_login = not st.session_state.show_login
        if st.session_state.show_login:
            with st.form("top_login"):
                u = st.text_input("ID", label_visibility="collapsed", placeholder="Admin ID")
                p = st.text_input("Pass", type="password", label_visibility="collapsed", placeholder="Password")
                if st.form_submit_button("เข้าสู่ระบบ"):
                    if u in st.secrets["users"] and p == st.secrets["users"][u]:
                        st.session_state.logged_in = True
                        st.session_state.admin_name = u
                        st.rerun()
                    else: st.error("ข้อมูลไม่ถูกต้อง")
    else:
        st.write(f"🛡️ **{st.session_state.admin_name}**")
        if st.button("🚪 ออกจากระบบ"):
            st.session_state.logged_in = False
            st.rerun()

# --- 4. การแสดงผลหน้าจอหลัก ---
if not st.session_state.logged_in:
    # --- หน้า Leaderboard (สำหรับนักเรียน) ---
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
    # --- หน้า Admin (บันทึกคะแนน + ระบบล็อกซ้ำ) ---
    st.markdown("### 🎯 ระบบบันทึกคะแนน")
    sh = get_sh()
    df_main = load_data()

    with st.container(border=True):
        sel_name = st.selectbox("เลือกนักเรียน", df_main.iloc[:, 0].dropna().tolist())
        days = [c for c in df_main.columns if "day" in str(c).lower()]
        sel_day = st.selectbox("เลือกกิจกรรม (Day)", days)
        pts = st.number_input("คะแนน", min_value=1, value=5, step=1)

        # --- ส่วนหัวใจ: ระบบตรวจสอบการบันทึกซ้ำจาก Logs ---
        log_ws = sh.worksheet("Logs")
        logs_df = pd.DataFrame(log_ws.get_all_records())
        today = datetime.now().strftime("%Y-%m-%d")
        
        is_duplicate = False
        if not logs_df.empty:
            # ตรวจสอบ: ชื่อตรงกัน และ ช่อง Day ตรงกัน และ วันที่บันทึกคือวันนี้
            logs_df['DateOnly'] = pd.to_datetime(logs_df['Timestamp']).dt.strftime("%Y-%m-%d")
            match = logs_df[(logs_df['Student'] == sel_name) & 
                            (logs_df['Day'] == sel_day) & 
                            (logs_df['DateOnly'] == today)]
            if not match.empty:
                is_duplicate = True

        # การควบคุมปุ่มบันทึก
        if is_duplicate:
            st.error(f"❌ วันนี้ลงคะแนนให้ '{sel_name}' ในช่อง '{sel_day}' ไปแล้ว ไม่สามารถบันทึกซ้ำได้")
            can_save = False
        else:
            can_save = True

        if st.button("🚀 ยืนยันบันทึกคะแนน", use_container_width=True, disabled=not can_save):
            try:
                # 1. บันทึกเจาะจงช่อง (Surgical Update) ไม่ยุ่งส่วนอื่น
                main_ws = sh.worksheet("Sheet1")
                row = main_ws.find(sel_name, in_column=1).row
                col = main_ws.find(sel_day, in_row=1).col
                old_v = main_ws.cell(row, col).value
                main_ws.update_cell(row, col, int(float(old_v or 0)) + pts)
                
                # 2. บันทึกลง Logs อัตโนมัติ
                log_ws.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    st.session_state.admin_name,
                    sel_name,
                    sel_day,
                    pts,
                    "Success"
                ])
                st.success(f"บันทึกสำเร็จ!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e: st.error(f"เกิดข้อผิดพลาด: {e}")

    # แสดงประวัติการบันทึกล่าสุด 5 รายการในหน้าแอดมินแทน Leaderboard เพื่อความเร็ว
    if not logs_df.empty:
        st.markdown("---")
        st.markdown("📜 **ประวัติการบันทึก 5 รายการล่าสุดของคุณ**")
        st.table(logs_df.tail(5)[['Timestamp', 'Student', 'Day', 'Points']])
