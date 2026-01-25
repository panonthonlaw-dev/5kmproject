import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. ตั้งค่าตัวแปรเริ่มต้น (ป้องกัน Error) ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "admin_name" not in st.session_state: st.session_state.admin_name = ""

# --- 2. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Patwit Admin System", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    [data-testid="block-container"] { padding: 1rem 0.5rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body { font-family: 'Sarabun', sans-serif; background-color: #f4f7f9; }
    
    /* สไตล์สำหรับการแสดงผล Leaderboard เฉพาะหน้าบ้าน */
    .leaderboard-grid { display: grid; grid-template-columns: repeat(5, 1fr) !important; gap: 4px; }
    .player-card { background: white; border-radius: 6px; padding: 8px 3px; text-align: center; border: 1px solid #eee; }
    .player-name { font-size: 2.5vw !important; font-weight: 600; line-height: 1.1; height: 5.5vw; overflow: hidden; }
    .score-num { font-size: 5vw !important; font-weight: 800; color: #1E88E5; }
    .rank-tag { font-size: 2vw; font-weight: 600; opacity: 0.6; }
    .c-1 { color: #FFD700; } .c-2 { color: #999; } .c-3 { color: #CD7F32; }
    
    @media (min-width: 1024px) {
        .player-card { padding: 15px; }
        .player-name { font-size: 1.1rem !important; height: 45px; }
        .score-num { font-size: 2.2rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ฟังก์ชันเชื่อมต่อข้อมูล ---
def get_sh():
    # ใช้ gspread สำหรับการบันทึกข้อมูล (เจาะจงช่อง ไม่ลบส่วนอื่น)
    conf = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(conf, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    s_id = conf.get("spreadsheet") or conf.get("url")
    return client.open_by_key(s_id) if len(s_id) < 60 else client.open_by_url(s_id)

def load_view_data():
    # ใช้ GSheetsConnection สำหรับการอ่านข้อมูลมาโชว์ (เร็วและง่าย)
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(worksheet="Sheet1", ttl="0s")

# --- 4. ระบบจัดการ Login ---
if not st.session_state.logged_in:
    # --- หน้า Leaderboard สำหรับนักเรียน (แสดงเฉพาะเมื่อยังไม่ล็อกอิน) ---
    st.markdown("<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)
    try:
        df_v = load_view_data()
        ld = df_v.iloc[:, [0, 37, 38, 39]].copy()
        ld.columns = ['Name', 'Score', 'EXP', 'Medal']
        ld['Score'] = pd.to_numeric(ld['Score'], errors='coerce').fillna(0).astype(int)
        ld['Rank'] = ld['Score'].rank(method='dense', ascending=False).astype(int)
        players = ld.sort_values(by=['Rank', 'Name']).to_dict('records')
        
        grid_h = '<div class="leaderboard-grid">'
        for p in players:
            r, icon = p['Rank'], ("👑" if p['Rank'] <= 3 else "🎖️")
            color = f"c-{r}" if r <= 3 else ""
            grid_h += f'<div class="player-card"><div class="rank-tag {color}">{icon} #{r}</div><div class="player-name">{p["Name"]}</div><div class="score-num">{p["Score"]}</div><div style="font-size:1.5vw; opacity:0.5;">คะแนนรวม</div></div>'
        st.markdown(grid_h + '</div>', unsafe_allow_html=True)
    except: st.info("กำลังดึงข้อมูล...")

    # ปุ่ม Login แอบไว้ด้านล่าง
    with st.expander("🔓 สำหรับแอดมิน"):
        with st.form("login_form"):
            u, p = st.text_input("ID"), st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state.logged_in = True
                    st.session_state.admin_name = u
                    st.rerun()
                else: st.error("ข้อมูลไม่ถูกต้อง")

else:
    # --- 5. หน้าแอดมิน (ตัด Leaderboard ออกแล้ว เพื่อความเร็ว) ---
    st.markdown(f"### 🛡️ ระบบจัดการคะแนน: {st.session_state.admin_name}")
    
    if st.button("🚪 ออกจากระบบ"):
        st.session_state.logged_in = False
        st.rerun()

    # ดึงข้อมูลมาเฉพาะส่วนที่จำเป็นต้องใช้ใน Form
    df_main = load_view_data()
    sh = get_sh()

    with st.container(border=True):
        st.subheader("🎯 บันทึกคะแนนรายบุคคล")
        sel_name = st.selectbox("เลือกนักเรียน", df_main.iloc[:, 0].dropna().tolist())
        days = [c for c in df_main.columns if "day" in str(c).lower()]
        sel_day = st.selectbox("เลือกช่องกิจกรรม (Day)", days)
        pts = st.number_input("จำนวนคะแนนที่ให้", min_value=1, value=5, step=1)

        # --- ระบบตรวจสอบการบันทึกซ้ำจาก Logs สดๆ ---
        log_ws = sh.worksheet("Logs")
        logs_all = log_ws.get_all_records()
        logs_df = pd.DataFrame(logs_all)
        
        today = datetime.now().strftime("%Y-%m-%d")
        is_duplicate = False
        
        if not logs_df.empty:
            logs_df['Date'] = pd.to_datetime(logs_df['Timestamp']).dt.strftime("%Y-%m-%d")
            match = logs_df[(logs_df['Student'] == sel_name) & (logs_df['Day'] == sel_day) & (logs_df['Date'] == today)]
            if not match.empty: is_duplicate = True

        if is_duplicate:
            st.error(f"❌ วันนี้ลงคะแนนให้ '{sel_name}' ในช่อง '{sel_day}' ไปแล้ว!")
            can_save = False
        else:
            can_save = True

        if st.button("🚀 บันทึกคะแนนลง Google Sheets", use_container_width=True, disabled=not can_save):
            try:
                # 1. บันทึกเจาะจงช่อง (Surgical Update)
                main_ws = sh.worksheet("Sheet1")
                row = main_ws.find(sel_name, in_column=1).row
                col = main_ws.find(sel_day, in_row=1).col
                old_v = main_ws.cell(row, col).value
                main_ws.update_cell(row, col, int(float(old_v or 0)) + pts)
                
                # 2. บันทึกลง Logs
                log_ws.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    st.session_state.admin_name,
                    sel_name,
                    sel_day,
                    pts,
                    "Success"
                ])
                st.success(f"บันทึกสำเร็จ! ข้อมูลถูกหยอดลงช่อง {sel_day} เรียบร้อย")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

    # แสดงประวัติการบันทึก 5 รายการล่าสุดในหน้า Admin (แทน Leaderboard)
    st.markdown("---")
    st.markdown("📜 **ประวัติการบันทึก 5 รายการล่าสุด**")
    if not logs_df.empty:
        st.table(logs_df.tail(5)[['Timestamp', 'Admin', 'Student', 'Day', 'Points']])
