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
    # ดึงข้อมูลมาแสดงหน้าแรก: ชื่อ(A), คะแนนรวม(AL), EXP(AM), ระดับเหรียญ(AN)
    data = df.iloc[:, [0, 37, 38, 39]].copy()
    data.columns = ['Name', 'Score', 'EXP', 'Medal']
    data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
    return df, data

def load_logs():
    try:
        return conn.read(worksheet="Logs", ttl="0s")
    except:
        return pd.DataFrame(columns=['Timestamp', 'Admin', 'Student', 'Day', 'Activity', 'Points', 'Status'])

# --- 3. การแมปคอลัมน์ Day (J-AK) ---
# J คือคอลัมน์ที่ 10 (index 9) จนถึง AK คือคอลัมน์ที่ 37 (index 36)
day_columns = {}
for i, day_num in enumerate(range(5, 31)):
    col_name = f"Day {day_num:02d}"
    day_columns[col_name] = 9 + i # Index 9 คือ J

# --- 4. ระบบ Admin Login ---
if "admin_user" not in st.session_state:
    if "admin_active" in st.query_params:
        st.session_state["admin_user"] = st.query_params.get("user", "Admin")
    else:
        st.session_state["admin_user"] = None

h_l, h_r = st.columns([20, 1])
with h_r:
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
            u, p = st.text_input("Admin User"), st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state["admin_user"] = u
                    st.query_params["admin_active"], st.query_params["user"] = "true", u
                    st.rerun()
                else: st.error("ข้อมูลไม่ถูกต้อง")

# --- 5. ส่วนหลังบ้าน (Admin Dashboard) ---
if st.session_state["admin_user"]:
    st.markdown(f"### 🛡️ ระบบหลังบ้าน: ลงคะแนนรายวัน (แอดมิน: {st.session_state['admin_user']})")
    
    # ดึงข้อมูลใหม่ทุกครั้งที่โหลดส่วนนี้เพื่อป้องกันข้อมูลซ้อน
    full_df = conn.read(worksheet="Sheet1", ttl="0s")
    student_data = full_df.iloc[:, [0, 37, 38, 39]].copy()
    student_data.columns = ['Name', 'Score', 'EXP', 'Medal']
    
    log_df = load_logs()
    
    with st.expander("🎯 บันทึกคะแนนรายวัน (J-AK)", expanded=True):
        selected_name = st.selectbox("🔍 ค้นหาชื่อนักเรียน", student_data['Name'].tolist())
        
        col_day, col_pts = st.columns(2)
        with col_day:
            selected_day = st.selectbox("เลือกวันที่ลงคะแนน", list(day_columns.keys()))
        with col_pts:
            pts = st.number_input("คะแนนที่ให้", min_value=1, max_value=50, value=5)

        # เช็คประวัติการให้คะแนนซ้ำ
        today_str = datetime.now().strftime("%Y-%m-%d")
        already_scored = False
        if not log_df.empty:
            log_df['DateOnly'] = pd.to_datetime(log_df['Timestamp']).dt.strftime("%Y-%m-%d")
            check = log_df[(log_df['Student'] == selected_name) & (log_df['Day'] == selected_day) & (log_df['DateOnly'] == today_str)]
            if not check.empty: already_scored = True

        if already_scored:
            st.warning(f"⚠️ {selected_name} ได้รับคะแนนของ {selected_day} ไปแล้วในวันนี้!")
            secret_code = st.text_input("ใส่รหัสลับเพื่อแก้ไขคะแนน", type="password")
            
        if st.button("🚀 บันทึกคะแนน", use_container_width=True):
            # ตรวจสอบรหัสลับถ้าเป็นการให้ซ้ำ
            can_proceed = True
            if already_scored:
                if secret_code != st.secrets["admin_secret_code"]["code"]:
                    st.error("รหัสลับไม่ถูกต้อง")
                    can_proceed = False
            
            if can_proceed:
                try:
                    # 1. ค้นหาแถวของนักเรียน (หาจากชื่อในคอลัมน์แรก)
                    # เราจะใช้ .values เพื่อความชัวร์ในการหาตำแหน่งแถว
                    row_mask = full_df.iloc[:, 0] == selected_name
                    row_idx = full_df.index[row_mask].tolist()[0]
                    
                    # 2. ค้นหาตำแหน่งคอลัมน์ (Day 05 - 30)
                    col_idx = day_columns[selected_day]
                    
                    # 3. คำนวณคะแนนใหม่
                    current_val = full_df.iloc[row_idx, col_idx]
                    # ถ้าช่องว่างให้เป็น 0 ถ้ามีค่าเดิมให้บวกเพิ่ม
                    new_val = (0 if pd.isna(current_val) or current_val == "" else float(current_val)) + pts
                    
                    # 4. อัปเดตค่าลงใน DataFrame หลัก
                    full_df.iloc[row_idx, col_idx] = new_val
                    
                    # 5. ส่งข้อมูลกลับไปที่ Google Sheets (Sheet1)
                    # ใช้คำสั่ง update โดยส่งทั้งแผ่นกลับไป
                    conn.update(worksheet="Sheet1", data=full_df)
                    
                    # 6. บันทึก Log ลงแผ่นงาน Logs
                    new_log = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Admin": st.session_state["admin_user"],
                        "Student": selected_name,
                        "Day": selected_day,
                        "Activity": "Daily Update",
                        "Points": pts,
                        "Status": "Edited" if already_scored else "New"
                    }])
                    updated_logs = pd.concat([log_df, new_log], ignore_index=True).drop(columns=['DateOnly'], errors='ignore')
                    conn.update(worksheet="Logs", data=updated_logs)
                    
                    st.success(f"บันทึกคะแนนให้ {selected_name} ในช่อง {selected_day} สำเร็จ!")
                    st.balloons()
                    
                    # ล้าง Cache เพื่อให้หน้า Leaderboard เห็นข้อมูลใหม่ทันที
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดขณะบันทึก: {e}")

# --- 6. หน้า Leaderboard (Public) ---
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
            <div class="rank-header" style="height:30px;">
                <div class="c-{r if r<=3 else 'normal'}" style="font-size:18px;">{icon} <span style="font-size:9px; color:gray;">#{r}</span></div>
            </div>
            <div style="font-size:0.85em; font-weight:600; height:35px; overflow:hidden;">{p['Name']}</div>
            <div><div class="score-num">{p['Score']:.0f}</div></div>
            <div style="font-size:0.6em; opacity:0.7; border-top:1px solid rgba(128,128,128,0.1); padding-top:4px;">⚡ EXP: {p['EXP']}<br>🏅 {p['Medal']}</div>
        </div>"""
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)
except: st.write("กำลังเชื่อมต่อข้อมูล...")
