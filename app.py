import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. การตั้งค่าหน้าเว็บและดีไซน์ (Custom CSS) ---
st.set_page_config(page_title="Patwit Leaderboard", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    /* ซ่อนแถบเมนู Streamlit */
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

    /* ระบบ Grid สำหรับ Leaderboard */
    .leaderboard-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        padding: 10px;
    }
    @media (max-width: 768px) {
        .leaderboard-grid { grid-template-columns: repeat(3, 1fr); gap: 8px; }
    }

    /* การ์ดผู้เล่น */
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
    .c-1 { color: #FFD700; filter: drop-shadow(0 0 3px rgba(255,215,0,0.5)); } 
    .c-2 { color: #C0C0C0; } 
    .c-3 { color: #CD7F32; }
    .score-num { font-size: 1.3em; font-weight: 800; color: var(--primary-color); }
    .card-footer { font-size: 0.65em; border-top: 1px solid rgba(128,128,128,0.1); padding-top: 5px; opacity: 0.8; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันการเชื่อมต่อข้อมูล ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_main_data():
    # ดึงข้อมูลจาก Sheet1 (ข้อมูลสดใหม่ตลอด)
    df = conn.read(worksheet="Sheet1", ttl="2s")
    return df

def load_logs():
    try:
        return conn.read(worksheet="Logs", ttl="0s")
    except:
        return pd.DataFrame(columns=['Timestamp', 'Admin', 'Student', 'Day', 'Points', 'Status'])

# --- 3. ระบบ Admin Authentication & Session ---
if "admin_user" not in st.session_state:
    if "admin_active" in st.query_params:
        st.session_state["admin_user"] = st.query_params.get("user", "Admin")
    else:
        st.session_state["admin_user"] = None

# ปุ่ม Login/Logout มุมขวาบน
h_col1, h_col2 = st.columns([20, 1])
with h_col2:
    if st.session_state["admin_user"] is None:
        if st.button("🔓"): st.session_state["show_login"] = not st.session_state.get("show_login", False)
    else:
        if st.button("🚪"): 
            st.session_state["admin_user"] = None
            st.query_params.clear()
            st.rerun()

# ฟอร์ม Login
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
    st.markdown(f"### 🛡️ ระบบจัดการคะแนนรายวัน (แอดมิน: {st.session_state['admin_user']})")
    
    full_df = load_main_data()
    log_df = load_logs()
    
    with st.expander("🎯 ลงคะแนนกิจกรรม Day 05 - 30", expanded=True):
        student_list = full_df.iloc[:, 0].dropna().tolist()
        sel_name = st.selectbox("🔍 ค้นหาชื่อนักเรียน", student_list)
        
        # สร้างตัวเลือก Day
        days_to_select = [f"day{i:02d}" for i in range(5, 31)]
        sel_day = st.selectbox("เลือกวันที่ลงคะแนน (จะไปลงที่คอลัมน์ชื่อนี้)", days_to_select)
        
        add_pts = st.number_input("คะแนนที่เพิ่ม", min_value=1, value=5)

        # เช็คประวัติการลงคะแนนซ้ำในวันนี้
        today_str = datetime.now().strftime("%Y-%m-%d")
        already_done = False
        if not log_df.empty:
            log_df['DateOnly'] = pd.to_datetime(log_df['Timestamp']).dt.strftime("%Y-%m-%d")
            check = log_df[(log_df['Student'] == sel_name) & (log_df['Day'] == sel_day) & (log_df['DateOnly'] == today_str)]
            if not check.empty: already_done = True

        secret_needed = False
        if already_done:
            st.warning(f"⚠️ วันนี้ {sel_name} เคยได้คะแนนของ {sel_day} ไปแล้ว!")
            secret_code = st.text_input("ระบุรหัสลับเพื่อบันทึกซ้ำ/แก้ไข", type="password")
            secret_needed = True

        if st.button("🚀 ยืนยันการบันทึก", use_container_width=True):
            can_save = True
            if secret_needed and secret_code != st.secrets["admin_secret_code"]["code"]:
                st.error("รหัสลับไม่ถูกต้อง")
                can_save = False
            
            if can_save:
                try:
                    # ค้นหาแถวและคอลัมน์
                    row_idx = full_df[full_df.iloc[:, 0] == sel_name].index[0]
                    target_col = None
                    for col in full_df.columns:
                        if str(col).strip().lower() == sel_day.lower():
                            target_col = col
                            break
                    
                    if target_col:
                        # อัปเดตคะแนน
                        current_val = full_df.at[row_idx, target_col]
                        new_val = (0 if pd.isna(current_val) or current_val == "" else float(current_val)) + add_pts
                        full_df.at[row_idx, target_col] = new_val
                        
                        # บันทึกลง Sheet1
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
                        updated_logs = pd.concat([log_df, new_log], ignore_index=True).drop(columns=['DateOnly'], errors='ignore')
                        conn.update(worksheet="Logs", data=updated_logs)
                        
                        st.success(f"ลงคะแนน {sel_day} ให้ {sel_name} เรียบร้อยแล้ว!")
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ ไม่พบคอลัมน์ชื่อ '{sel_day}' ใน Google Sheets (แถวที่ 1)")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

    with st.expander("📜 ตรวจสอบประวัติ (Logs)"):
        st.dataframe(log_df.sort_values(by="Timestamp", ascending=False), use_container_width=True)

# --- 5. หน้าบ้าน: Leaderboard (Public) ---
st.markdown("<h2 style='text-align: center;'>🏆 ทำเนียบผู้กล้า</h2>", unsafe_allow_html=True)

try:
    display_df = load_main_data()
    # ดึงเฉพาะคอลัมน์ A(ชื่อ), AL(คะแนนรวม), AM(EXP), AN(เหรียญ)
    # หมายเหตุ: AL คือตำแหน่งที่ 38 (Index 37)
    ld_data = display_df.iloc[:, [0, 37, 38, 39]].copy()
    ld_data.columns = ['Name', 'Score', 'EXP', 'Medal']
    ld_data['Score'] = pd.to_numeric(ld_data['Score'], errors='coerce')
    
    df_clean = ld_data.dropna(subset=['Score']).copy()
    df_clean['Rank'] = df_clean['Score'].rank(method='dense', ascending=False).astype(int)
    players = df_clean.sort_values(by='Rank').to_dict('records')

    # สร้าง Grid การแสดงผล
    grid_html = '<div class="leaderboard-grid">'
    for p in players:
        r = p['Rank']
        icon = "👑" if r <= 3 else "🎖️"
        c_class = f"c-{r}" if r <= 3 else "c-normal"
        
        grid_html += f"""
        <div class="player-card">
            <div class="rank-header">
                <div class="{c_class}" style="font-size:18px;">{icon} <span style="font-size:9px; color:gray;">#{r}</span></div>
            </div>
            <div style="font-size:0.85em; font-weight:600; height:35px; overflow:hidden; line-height:1.2;">{p['Name']}</div>
            <div>
                <div style="font-size:0.55em; opacity:0.6;">คะแนนรวม</div>
                <div class="score-num">{p['Score']:.0f}</div>
            </div>
            <div class="card-footer">
                ⚡ EXP: {p['EXP']}<br>🏅 {p['Medal']}
            </div>
        </div>"""
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

except Exception as e:
    st.info("💡 กำลังดึงข้อมูลจากทำเนียบผู้กล้า...")
