import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าเว็บและซ่อน UI ของระบบ ---
st.set_page_config(page_title="Gaming Leaderboard", page_icon="👑", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    /* ซ่อนแถบเมนูและส่วนหัวของระบบ */
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { 
        visibility: hidden; display: none; 
    }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

    /* ระบบ Grid สำหรับหน้าจอหลัก */
    .leaderboard-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        padding: 10px;
    }
    @media (max-width: 768px) {
        .leaderboard-grid { grid-template-columns: repeat(3, 1fr); gap: 8px; }
    }

    /* ดีไซน์การ์ดผู้เล่น */
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
    .card-footer { font-size: 0.65em; border-top: 1px solid rgba(128, 128, 128, 0.1); padding-top: 5px; opacity: 0.8; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ระบบรักษาความปลอดภัยและจำสถานะ (Admin) ---
if "admin_auth" not in st.session_state:
    if "admin_active" in st.query_params:
        st.session_state["admin_auth"] = True
    else:
        st.session_state["admin_auth"] = False

# --- 3. ส่วนหัวของเว็บและปุ่ม Login มุมขวาบน ---
# ใช้ columns เพื่อผลักปุ่มไปทางขวาสุด
header_left, header_right = st.columns([15, 1])

with header_right:
    if not st.session_state["admin_auth"]:
        if st.button("🔓", help="Admin Login"):
            st.session_state["show_login"] = not st.session_state.get("show_login", False)
    else:
        if st.button("🚪", help="Logout Admin"):
            st.session_state["admin_auth"] = False
            st.query_params.clear()
            st.rerun()

# ฟอร์ม Login (จะปรากฏเมื่อกดปุ่ม 🔓)
if not st.session_state["admin_auth"] and st.session_state.get("show_login", False):
    _, login_col, _ = st.columns([2, 1, 2])
    with login_col:
        with st.form("admin_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("ยืนยัน Admin"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state["admin_auth"] = True
                    st.query_params["admin_active"] = "true"
                    st.session_state["show_login"] = False
                    st.rerun()
                else: st.error("ข้อมูลไม่ถูกต้อง")

# --- 4. การจัดการข้อมูลและการแสดงผล ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(ttl="10s")
    data = df.iloc[:, [0, 37, 38, 39]].copy()
    data.columns = ['Name', 'Score', 'EXP', 'Medal']
    data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
    return df, data

# แสดงเมนูหลังบ้านถ้า Login แล้ว
if st.session_state["admin_auth"]:
    st.markdown("---")
    st.markdown("### 🎯 ระบบหลังบ้าน: ให้คะแนนกิจกรรม")
    full_df, data = load_data()
    with st.container(border=True):
        col_s, col_a, col_p = st.columns([2, 2, 1])
        with col_s: sel_name = st.selectbox("เลือกนักเรียน", data['Name'].tolist())
        with col_a: act_type = st.selectbox("กิจกรรม", ["หน้าเสาธง", "จิตอาสา", "ในห้องเรียน", "งานค้าง", "อื่นๆ"])
        with col_p: add_pts = st.number_input("คะแนน", min_value=1, value=5)
        
        if st.button("🚀 บันทึกคะแนน", use_container_width=True):
            row_idx = full_df[full_df.iloc[:, 0] == sel_name].index[0]
            current_val = full_df.iloc[row_idx, 37]
            full_df.iloc[row_idx, 37] = (0 if pd.isna(current_val) else current_val) + add_pts
            conn.update(worksheet="Sheet1", data=full_df)
            st.success(f"อัปเดต {sel_name} สำเร็จ!")
            st.balloons()
    st.markdown("---")

# --- 5. หน้า Leaderboard (Public) ---
st.markdown("<h2 style='text-align: center;'>🏆 ทำเนียบผู้กล้า</h2>", unsafe_allow_html=True)

try:
    _, data = load_data()
    df_c = data.dropna(subset=['Score']).copy()
    df_c['Rank'] = df_c['Score'].rank(method='dense', ascending=False).astype(int)
    players = df_c.sort_values(by='Rank').to_dict('records')

    # สร้าง Grid ด้วย HTML
    grid_html = '<div class="leaderboard-grid">'
    for p in players:
        r = p['Rank']
        icon = "👑" if r <= 3 else "🎖️"
        c_class = f"c-{r}" if r <= 3 else ""
        grid_html += f"""
        <div class="player-card">
            <div>
                <div class="{c_class}" style="font-size:18px;">{icon}</div>
                <div style="font-size:8px; opacity:0.6;">RANK {r}</div>
            </div>
            <div style="font-size:0.85em; font-weight:600; height:30px; overflow:hidden;">{p['Name']}</div>
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
    st.error("กำลังเชื่อมต่อข้อมูล...")
