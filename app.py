import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Gaming Leaderboard", page_icon="🏆", layout="wide")

# --- 2. CSS: บังคับ Grid, ซ่อนเมนูระบบ และดีไซน์การ์ด ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { 
        visibility: hidden; display: none; 
    }

    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

    /* ระบบ Grid */
    .leaderboard-container {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        padding: 10px;
    }

    @media (max-width: 768px) {
        .leaderboard-container { grid-template-columns: repeat(3, 1fr); gap: 8px; }
    }

    /* การ์ดผู้เล่น */
    .player-box {
        background-color: var(--secondary-background-color);
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.1);
        min-height: 155px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .crown-zone { height: 35px; }
    .crown-img { font-size: 20px; line-height: 1; }
    .rank-tag { font-size: 9px; font-weight: bold; opacity: 0.7; }
    .c-1 { color: #FFD700; } .c-2 { color: #C0C0C0; } .c-3 { color: #CD7F32; }

    .p-name { font-size: 0.9em; font-weight: 600; margin: 5px 0; height: 35px; overflow: hidden; line-height: 1.2; }
    .score-label { font-size: 0.6em; opacity: 0.6; }
    .score-big { font-size: 1.3em; font-weight: 800; color: var(--primary-color); margin-bottom: 5px; }
    
    .stats-footer { 
        font-size: 0.65em; 
        border-top: 1px solid rgba(128, 128, 128, 0.1); 
        padding-top: 5px; 
        opacity: 0.8;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ระบบจัดการสถานะ Admin ---
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

# ส่วนของ Admin ใน Sidebar
with st.sidebar:
    if not st.session_state["admin_authenticated"]:
        st.markdown("### 🔒 Admin Access")
        with st.form("admin_login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state["admin_authenticated"] = True
                    st.success("Admin Logged In!")
                    st.rerun()
                else:
                    st.error("Invalid Login")
    else:
        st.markdown(f"### ✅ Admin Mode")
        st.write(f"Logged in as: **Admin**")
        # พื้นที่สำหรับระบบหลังบ้านในอนาคต
        st.info("ระบบหลังบ้านจะถูกเพิ่มในส่วนนี้")
        if st.button("Logout"):
            st.session_state["admin_authenticated"] = False
            st.rerun()

# --- 4. การแสดงผล Leaderboard (Public) ---
st.markdown("<h2 style='text-align: center;'>🏆 ทำเนียบผู้กล้า</h2>", unsafe_allow_html=True)

try:
    # ดึงข้อมูลจาก Google Sheets
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="1m")

    if df is not None:
        # ดึงคอลัมน์ A(0), AL(37), AM(38), AN(39)
        data = df.iloc[:, [0, 37, 38, 39]].copy()
        data.columns = ['Name', 'Score', 'EXP', 'Medal']
        data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
        
        # คำนวณอันดับแบบไม่ข้ามเลข (Dense Ranking)
        df_clean = data.dropna(subset=['Score']).copy()
        df_clean['Rank'] = df_clean['Score'].rank(method='dense', ascending=False).astype(int)
        players = df_clean.sort_values(by='Rank').to_dict('records')

        # เริ่มสร้าง HTML Grid
        grid_html = '<div class="leaderboard-container">'
        
        for p in players:
            r = p['Rank']
            c_class = f"c-{r}" if r <= 3 else ""
            icon = "👑" if r <= 3 else "🎖️"
            
            grid_html += f"""
            <div class="player-box">
                <div class="crown-zone">
                    <div class="crown-img {c_class}">{icon}</div>
                    <div class="rank-tag">RANK {r}</div>
                </div>
                <div class="p-name">{p['Name']}</div>
                <div>
                    <div class="score-label">คะแนนรวม</div>
                    <div class="score-big">{p['Score']:.0f}</div>
                </div>
                <div class="stats-footer">
                    ⚡ EXP: {p['EXP']}<br>🏅 ระดับเหรียญ: {p['Medal']}
                </div>
            </div>
            """
        
        grid_html += '</div>'
        st.markdown(grid_html, unsafe_allow_html=True)

except Exception as e:
    st.error("ไม่สามารถเชื่อมต่อข้อมูลได้")
