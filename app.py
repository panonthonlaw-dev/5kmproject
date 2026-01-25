import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. การตั้งค่าหน้าเว็บและดีไซน์ ---
st.set_page_config(page_title="Patwit Leaderboard", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

    .leaderboard-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        padding: 10px;
    }
    @media (max-width: 768px) {
        .leaderboard-grid { grid-template-columns: repeat(3, 1fr); gap: 8px; }
    }

    .player-card {
        background-color: var(--secondary-background-color);
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.1);
        min-height: 155px;
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .c-1 { color: #FFD700; } .c-2 { color: #C0C0C0; } .c-3 { color: #CD7F32; }
    .score-num { font-size: 1.3em; font-weight: 800; color: var(--primary-color); }
    .card-footer { font-size: 0.65em; border-top: 1px solid rgba(128,128,128,0.1); padding-top: 5px; opacity: 0.8; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันการเชื่อมต่อข้อมูล ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_main_data():
    return conn.read(worksheet="Sheet1", ttl="2s")

def load_logs():
    try:
        return conn.read(worksheet="Logs", ttl="0s")
    except:
        return pd.DataFrame(columns=['Timestamp', 'Admin', 'Student', 'Day', 'Points', 'Status'])

# --- 3. ระบบ Admin Login ---
if "admin_user" not in st.session_state:
    if "admin_active" in st.query_params:
        st.session_state["admin_user"] = st.query_params.get("user", "Admin")
    else:
        st.session_state["admin_user"] = None

h_col1, h_col2 = st.columns([20, 1])
with h_col2:
    if st.session_state["admin_user"] is None:
        if st.button("🔓"): st.session_state["show_login"] = not st.session_state.get("show_login", False)
    else:
        if st.button("🚪"): 
            st.session_state["admin_user"] = None
            st.query_params.clear()
            st.rerun()

if st.session_state["admin_user"] is None and st.session_state.get("show_login", False):
    _, l_col, _ = st.columns([2, 1, 2])
    with l_col:
        with st.form("admin_login"):
            u, p = st.text_input("Admin ID"), st.text_input("Password", type="password")
            if st.form_submit_button("เข้าสู่ระบบ"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state["admin_user"] = u
                    st.query_params["admin_active"], st.query_params["user"] = "true", u
                    st.session_state["show_login"] = False
                    st.rerun()
                else: st.error("รหัสผ่านไม่ถูกต้อง")

# --- 4. ส่วนหลังบ้าน (Admin Panel) ---
if st.session_state["admin_user"]:
    st.markdown(f"### 🛡️ ระบบจัดการคะแนน (แอดมิน: {st.session_state['admin_user']})")
    
    full_df = load_main_data()
    log_df = load_logs()
    
    with st.expander("🎯 ค้นหาและลงคะแนนรายวัน", expanded=True):
        # --- ระบบค้นหาอัจฉริยะ ---
        search_query = st.text_input("🔍 พิมพ์ชื่อนักเรียนเพื่อค้นหา", placeholder="เช่น สมชาย, เด็กหญิง...")
        
        student_list = full_df.iloc[:, 0].dropna().tolist()
        
        # กรองรายชื่อตามที่พิมพ์ค้นหา
        filtered_list = [s for s in student_list if search_query.lower() in str(s).lower()] if search_query else student_list
        
        if not filtered_list:
            st.warning("❌ ไม่พบรายชื่อที่ตรงกับการค้นหา")
            sel_name = None
        else:
            sel_name = st.selectbox(f"เลือกนักเรียนจากผลการค้นหา ({len(filtered_list)} คน)", filtered_list)

        if sel_name:
            # ดึงข้อมูลมาโชว์ก่อนให้คะแนน
            student_row = full_df[full_df.iloc[:, 0] == sel_name].iloc[0]
            st.info(f"👤 **กำลังจัดการข้อมูลของ:** {sel_name} | **คะแนนรวมปัจจุบัน:** {student_row.iloc[37]} แต้ม")

            # ดึงชื่อคอลัมน์ Day มาให้เลือกอัตโนมัติ (กัน Error ชื่อคอลัมน์ไม่ตรง)
            actual_days = [col for col in full_df.columns if "day" in str(col).lower()]
            
            col_d, col_p = st.columns(2)
            with col_d:
                sel_day = st.selectbox("เลือกวันที่ลงคะแนน", actual_days) if actual_days else st.error("ไม่พบช่อง 'day' ใน Sheet")
            with col_p:
                add_pts = st.number_input("จำนวนคะแนนที่ให้", min_value=1, value=5)

            # เช็คการให้ซ้ำ
            today_str = datetime.now().strftime("%Y-%m-%d")
            already_done = False
            if not log_df.empty:
                log_df['DateOnly'] = pd.to_datetime(log_df['Timestamp']).dt.strftime("%Y-%m-%d")
                check = log_df[(log_df['Student'] == sel_name) & (log_df['Day'] == sel_day) & (log_df['DateOnly'] == today_str)]
                if not check.empty: already_done = True

            if already_done:
                st.warning(f"⚠️ วันนี้ให้คะแนน {sel_day} ของนักเรียนคนนี้ไปแล้ว")
                secret_code = st.text_input("ใส่รหัสลับเพื่อบันทึกซ้ำ", type="password")

            if st.button("🚀 ยืนยันบันทึกคะแนน", use_container_width=True):
                if already_done and secret_code != st.secrets["admin_secret_code"]["code"]:
                    st.error("รหัสลับไม่ถูกต้อง")
                elif sel_day:
                    try:
                        row_idx = full_df[full_df.iloc[:, 0] == sel_name].index[0]
                        current_val = full_df.at[row_idx, sel_day]
                        new_val = (0 if pd.isna(current_val) or current_val == "" else float(current_val)) + add_pts
                        full_df.at[row_idx, sel_day] = new_val
                        
                        conn.update(worksheet="Sheet1", data=full_df)
                        
                        # บันทึก Log
                        new_log = pd.DataFrame([{
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Admin": st.session_state["admin_user"],
                            "Student": sel_name,
                            "Day": sel_day,
                            "Points": add_pts,
                            "Status": "Updated" if already_done else "New"
                        }])
                        conn.update(worksheet="Logs", data=pd.concat([log_df, new_log], ignore_index=True).drop(columns=['DateOnly'], errors='ignore'))
                        
                        st.success(f"บันทึก {add_pts} คะแนน ลงใน {sel_day} เรียบร้อย!")
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")

    with st.expander("📜 ตรวจสอบประวัติการให้คะแนน"):
        st.dataframe(log_df.sort_values(by="Timestamp", ascending=False), use_container_width=True)

# --- 5. หน้าบ้าน: Leaderboard (Public) ---
st.markdown("<h2 style='text-align: center;'>🏆 ทำเนียบผู้กล้า</h2>", unsafe_allow_html=True)

try:
    display_df = load_main_data()
    ld_data = display_df.iloc[:, [0, 37, 38, 39]].copy()
    ld_data.columns = ['Name', 'Score', 'EXP', 'Medal']
    ld_data['Score'] = pd.to_numeric(ld_data['Score'], errors='coerce')
    
    df_clean = ld_data.dropna(subset=['Score']).copy()
    df_clean['Rank'] = df_clean['Score'].rank(method='dense', ascending=False).astype(int)
    players = df_clean.sort_values(by='Rank').to_dict('records')

    grid_html = '<div class="leaderboard-grid">'
    for p in players:
        r = p['Rank']
        icon = "👑" if r <= 3 else "🎖️"
        grid_html += f"""
        <div class="player-card">
            <div style="height:30px;"><div class="c-{r if r<=3 else 'normal'}" style="font-size:18px;">{icon} <span style="font-size:9px; color:gray;">#{r}</span></div></div>
            <div style="font-size:0.85em; font-weight:600; height:35px; overflow:hidden;">{p['Name']}</div>
            <div><div class="score-num">{p['Score']:.0f}</div></div>
            <div class="card-footer">⚡ EXP: {p['EXP']}<br>🏅 {p['Medal']}</div>
        </div>"""
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)
except: st.info("💡 กำลังดึงข้อมูลล่าสุด...")
