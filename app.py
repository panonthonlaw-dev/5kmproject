import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Gaming Leaderboard", page_icon="🏆", layout="wide")

# --- 2. CSS: บังคับ Grid และดีไซน์การ์ด ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

    .leaderboard-container {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        padding: 10px;
    }
    @media (max-width: 768px) {
        .leaderboard-container { grid-template-columns: repeat(3, 1fr); gap: 8px; }
    }
    .player-box {
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
    .score-big { font-size: 1.3em; font-weight: 800; color: var(--primary-color); }
    .stats-footer { font-size: 0.65em; border-top: 1px solid rgba(128, 128, 128, 0.1); padding-top: 5px; opacity: 0.8; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. การเชื่อมต่อข้อมูล ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(ttl="10s") # ตั้งค่าให้รีเฟรชเร็วขึ้นเมื่อมีการอัปเดต
    # คอลัมน์ A(0), AL(37), AM(38), AN(39)
    data = df.iloc[:, [0, 37, 38, 39]].copy()
    data.columns = ['Name', 'Score', 'EXP', 'Medal']
    data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
    return df, data

# --- 4. ระบบ Admin ใน Sidebar ---
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

with st.sidebar:
    if not st.session_state["admin_authenticated"]:
        st.markdown("### 🔒 Admin Access")
        with st.form("admin_login"):
            u, p = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state["admin_authenticated"] = True
                    st.rerun()
                else: st.error("Invalid Login")
    else:
        st.markdown(f"### ✅ Admin Mode")
        admin_page = st.radio("เมนูจัดการ", ["🏠 หน้าหลัก", "🎯 ให้คะแนนกิจกรรม"])
        if st.button("Logout"):
            st.session_state["admin_authenticated"] = False
            st.rerun()

# --- 5. ส่วนหน้าบ้าน (Leaderboard) ---
if not st.session_state["admin_authenticated"] or admin_page == "🏠 หน้าหลัก":
    st.markdown("<h2 style='text-align: center;'>🏆 ทำเนียบผู้กล้า</h2>", unsafe_allow_html=True)
    try:
        _, data = load_data()
        df_clean = data.dropna(subset=['Score']).copy()
        df_clean['Rank'] = df_clean['Score'].rank(method='dense', ascending=False).astype(int)
        players = df_clean.sort_values(by='Rank').to_dict('records')

        grid_html = '<div class="leaderboard-container">'
        for p in players:
            r = p['Rank']
            icon = "👑" if r <= 3 else "🎖️"
            c_class = f"c-{r}" if r <= 3 else ""
            grid_html += f"""
            <div class="player-box">
                <div>
                    <div class="{c_class}" style="font-size:20px;">{icon}</div>
                    <div style="font-size:9px; opacity:0.7;">RANK {r}</div>
                </div>
                <div style="font-size:0.9em; font-weight:600; height:35px; overflow:hidden;">{p['Name']}</div>
                <div><div style="font-size:0.6em; opacity:0.6;">คะแนนรวม</div><div class="score-big">{p['Score']:.0f}</div></div>
                <div class="stats-footer">⚡ EXP: {p['EXP']}<br>🏅 {p['Medal']}</div>
            </div>"""
        grid_html += '</div>'
        st.markdown(grid_html, unsafe_allow_html=True)
    except: st.error("Connection Error")

# --- 6. ส่วนหลังบ้าน: หมวดหมู่การให้คะแนนกิจกรรม ---
elif st.session_state["admin_authenticated"] and admin_page == "🎯 ให้คะแนนกิจกรรม":
    st.markdown("## 🎯 หมวดหมู่การให้คะแนนกิจกรรม")
    st.write("เลือกนักเรียนและระบุคะแนนที่ได้รับจากกิจกรรม")
    
    full_df, data = load_data()
    
    with st.container(border=True):
        student_list = data['Name'].tolist()
        selected_student = st.selectbox("เลือกนักเรียน", student_list)
        
        col_act, col_pts = st.columns([2, 1])
        with col_act:
            activity = st.selectbox("หมวดหมู่กิจกรรม", ["กิจกรรมหน้าเสาธง", "จิตอาสา", "ตอบคำถามในห้อง", "ส่งงานตรงเวลา", "อื่นๆ"])
        with col_pts:
            points = st.number_input("คะแนนที่ได้", min_value=1, max_value=50, value=5)

        if st.button("🚀 บันทึกคะแนน", use_container_width=True):
            # ค้นหาแถวของนักเรียนใน Google Sheets (คอลัมน์ A คือ index 0)
            # และอัปเดตคอลัมน์ AL (index 37)
            row_idx = full_df[full_df.iloc[:, 0] == selected_student].index[0]
            current_score = full_df.iloc[row_idx, 37]
            
            # ตรวจสอบว่าเป็นตัวเลขหรือไม่ ถ้าไม่ใช่ให้เริ่มที่ 0
            if pd.isna(current_score): current_score = 0
            
            # อัปเดตคะแนน
            full_df.iloc[row_idx, 37] = current_score + points
            
            # ส่งข้อมูลกลับไปยัง Google Sheets
            conn.update(worksheet="Sheet1", data=full_df)
            
            st.success(f"บันทึกสำเร็จ! {selected_student} ได้รับ {points} คะแนน จาก{activity}")
            st.balloons()
            st.info("คะแนนในหน้า Leaderboard จะอัปเดตภายในไม่กี่วินาที")
