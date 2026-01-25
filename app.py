import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Gaming Leaderboard", page_icon="👑", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    .leaderboard-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; padding: 10px; }
    @media (max-width: 768px) { .leaderboard-grid { grid-template-columns: repeat(3, 1fr); gap: 8px; } }
    .player-card { background-color: var(--secondary-background-color); border-radius: 12px; padding: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid rgba(128, 128, 128, 0.1); min-height: 155px; display: flex; flex-direction: column; justify-content: space-between; }
    .c-1 { color: #FFD700; } .c-2 { color: #C0C0C0; } .c-3 { color: #CD7F32; }
    .score-num { font-size: 1.3em; font-weight: 800; color: var(--primary-color); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. การเชื่อมต่อข้อมูล ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(worksheet="Sheet1", ttl="5s")
    data = df.iloc[:, [0, 37, 38, 39]].copy()
    data.columns = ['Name', 'Score', 'EXP', 'Medal']
    data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
    return df, data

def load_logs():
    try:
        return conn.read(worksheet="Logs", ttl="0s")
    except:
        return pd.DataFrame(columns=['Timestamp', 'Admin', 'Student', 'Activity', 'Points', 'Status'])

# --- 3. ระบบ Admin & Login ---
if "admin_user" not in st.session_state:
    st.session_state["admin_user"] = None

# ปุ่ม Login/Logout มุมขวาบน
h_l, h_r = st.columns([20, 1])
with h_r:
    if st.session_state["admin_user"] is None:
        if st.button("🔓"): st.session_state["show_login"] = not st.session_state.get("show_login", False)
    else:
        if st.button("🚪"): 
            st.session_state["admin_user"] = None
            st.rerun()

if st.session_state["admin_user"] is None and st.session_state.get("show_login", False):
    _, l_col, _ = st.columns([2, 1, 2])
    with l_col:
        with st.form("admin_login"):
            u, p = st.text_input("Admin User"), st.text_input("Password", type="password")
            if st.form_submit_button("เข้าสู่ระบบ"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state["admin_user"] = u
                    st.session_state["show_login"] = False
                    st.rerun()
                else: st.error("รหัสผ่านไม่ถูกต้อง")

# --- 4. ส่วนหลังบ้าน (Admin Dashboard) ---
if st.session_state["admin_user"]:
    st.markdown(f"### 🛡️ ระบบจัดการหลังบ้าน (แอดมิน: {st.session_state['admin_user']})")
    full_df, student_data = load_data()
    log_df = load_logs()
    
    with st.expander("🎯 บันทึกคะแนนกิจกรรม (จำกัดวันละ 1 ครั้ง)", expanded=True):
        # ระบบค้นหาชื่อ (st.selectbox มีระบบ Search ในตัว)
        selected_name = st.selectbox("🔍 ค้นหาชื่อนักเรียน", student_data['Name'].tolist())
        
        # ตรวจสอบว่าวันนี้ให้คะแนนไปหรือยัง
        today_str = datetime.now().strftime("%Y-%m-%d")
        # แปลง Timestamp ใน log เป็นวันที่เพื่อเช็ค
        already_scored = False
        if not log_df.empty:
            log_df['Date'] = pd.to_datetime(log_df['Timestamp']).dt.strftime("%Y-%m-%d")
            check = log_df[(log_df['Student'] == selected_name) & (log_df['Date'] == today_str)]
            if not check.empty: already_scored = True

        col_a, col_p = st.columns(2)
        with col_a: act = st.text_input("กิจกรรม", value="กิจกรรมพิเศษ")
        with col_p: pts = st.number_input("คะแนน", min_value=1, value=5)
        
        secret_needed = False
        if already_scored:
            st.warning(f"⚠️ นักเรียนคนนี้ได้รับคะแนนไปแล้วในวันนี้!")
            secret_code = st.text_input("กรุณาใส่รหัสลับเพื่อดำเนินการต่อ (แก้ไขคะแนน)", type="password")
            secret_needed = True
        
        if st.button("🚀 ยืนยันการให้คะแนน", use_container_width=True):
            # ตรวจสอบรหัสลับถ้าจำเป็น (สมมติรหัสลับคือ 'superadmin123' สามารถแก้ใน secrets ได้)
            if secret_needed and secret_code != st.secrets.get("admin_secret_code", "1234"):
                st.error("รหัสลับไม่ถูกต้อง! ไม่สามารถแก้ไขข้อมูลได้")
            else:
                # อัปเดตคะแนนใน Sheet หลัก
                row_idx = full_df[full_df.iloc[:, 0] == selected_name].index[0]
                full_df.iloc[row_idx, 37] = (0 if pd.isna(full_df.iloc[row_idx, 37]) else full_df.iloc[row_idx, 37]) + pts
                conn.update(worksheet="Sheet1", data=full_df)
                
                # บันทึก Log
                new_log = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Admin": st.session_state["admin_user"],
                    "Student": selected_name,
                    "Activity": act,
                    "Points": pts,
                    "Status": "Edited" if already_scored else "New"
                }])
                updated_logs = pd.concat([log_df, new_log], ignore_index=True).drop(columns=['Date'], errors='ignore')
                conn.update(worksheet="Logs", data=updated_logs)
                
                st.success(f"บันทึกสำเร็จสำหรับ {selected_name}!")
                st.balloons()
                st.rerun()

    with st.expander("📜 ประวัติการให้คะแนน (Logs)"):
        st.dataframe(load_logs().sort_values(by="Timestamp", ascending=False), use_container_width=True)

# --- 5. หน้า Leaderboard (Public) ---
st.markdown("<h2 style='text-align: center;'>🏆 ทำเนียบผู้กล้า</h2>", unsafe_allow_html=True)
try:
    _, data = load_data()
    df_c = data.dropna(subset=['Score']).copy()
    df_c['Rank'] = df_c['Score'].rank(method='dense', ascending=False).astype(int)
    players = df_c.sort_values(by='Rank').to_dict('records')

    grid_html = '<div class="leaderboard-grid">'
    for p in players:
        r = p['Rank']
        icon = "👑" if r <= 3 else "🎖️"
        grid_html += f"""
        <div class="player-card">
            <div class="crown-icon c-{r if r<=3 else 'normal'}" style="font-size:18px;">{icon} <span style="font-size:9px; color:gray;">#{r}</span></div>
            <div style="font-size:0.85em; font-weight:600; height:35px; overflow:hidden;">{p['Name']}</div>
            <div><div style="font-size:1.1em; font-weight:800;">{p['Score']:.0f}</div></div>
            <div style="font-size:0.6em; opacity:0.7; border-top:1px solid #eee; padding-top:4px;">⚡ EXP: {p['EXP']}<br>🏅 {p['Medal']}</div>
        </div>"""
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)
except: st.write("กำลังรอข้อมูล...")
