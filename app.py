import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. การตั้งค่าหน้าเว็บและ CSS (Professional Layout) ---
st.set_page_config(page_title="Patwit Leaderboard", page_icon="👑", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    /* ล้าง Padding ส่วนเกินของ Streamlit ออกเพื่อให้เห็น 5 คอลัมน์เต็มตา */
    [data-testid="block-container"] { padding: 1rem 0.5rem; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; overflow-x: hidden; }

    /* บังคับ 5 คอลัมน์เป๊ะๆ 100% ของความกว้างหน้าจอ */
    .leaderboard-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr) !important;
        gap: 4px; /* ระยะห่างเล็กลงเพื่อให้ดูแพงและคมชัด */
        width: 100%;
        box-sizing: border-box;
    }

    .player-card {
        background-color: #ffffff;
        border-radius: 6px;
        padding: 8px 4px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #eee;
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
        min-height: 150px; /* เพิ่มความสูงเพื่อให้มีที่ว่างพอ */
    }

    /* ตกแต่งลำดับ */
    .rank-tag { font-size: 2.2vw !important; font-weight: 600; opacity: 0.7; }
    .c-1 { color: #FFD700; } .c-2 { color: #999; } .c-3 { color: #CD7F32; }

    /* ชื่อนักเรียน - ตัดคำถ้าเกิน 2 บรรทัด */
    .player-name {
        font-size: 2.4vw !important;
        font-weight: 600;
        line-height: 1.2;
        height: 5.8vw;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin: 4px 0;
        color: #333;
    }
    
    /* คะแนนรวม */
    .score-container { margin: 5px 0; }
    .label-score { font-size: 1.8vw !important; opacity: 0.6; display: block; }
    .score-num { 
        font-size: 4vw !important; 
        font-weight: 800; 
        color: #1E88E5;
        line-height: 1;
    }
    
    /* Footer: บังคับให้อยู่บรรทัดเดียวกัน */
    .card-footer { 
        border-top: 1px solid #f5f5f5; 
        padding-top: 5px; 
        margin-top: auto;
    }
    
    .data-row {
        display: flex;
        justify-content: space-between; /* แยกซ้าย-ขวา */
        align-items: center;
        width: 100%;
        margin-bottom: 2px;
    }

    .data-label { font-size: 1.8vw !important; font-weight: 400; color: #777; }
    .data-val { 
        font-size: 1.8vw !important; 
        font-weight: 600; 
        color: #333; 
        max-width: 60%; 
        overflow: hidden; 
        text-overflow: ellipsis; 
        white-space: nowrap; /* ห้ามขึ้นบรรทัดใหม่ */
    }

    /* สำหรับหน้าจอคอมพิวเตอร์ (ล็อกขนาดไม่ให้ใหญ่เกินไป) */
    @media (min-width: 1024px) {
        [data-testid="block-container"] { padding: 2rem 5rem; }
        .leaderboard-grid { gap: 15px; }
        .player-card { min-height: 180px; padding: 15px; }
        .player-name { font-size: 1rem !important; height: 40px; }
        .score-num { font-size: 2rem !important; }
        .data-label, .data-val, .label-score, .rank-tag { font-size: 0.75rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันจัดการข้อมูล ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_main_data():
    return conn.read(worksheet="Sheet1", ttl="2s")

# --- 3. ระบบ Authentication (Admin) ---
if "admin_user" not in st.session_state:
    st.session_state["admin_user"] = None

h_l, h_r = st.columns([20, 1])
with h_r:
    if st.session_state["admin_user"] is None:
        if st.button("🔓"): st.session_state["show_login"] = not st.session_state.get("show_login", False)
    else:
        if st.button("🚪"): 
            st.session_state["admin_user"] = None
            st.rerun()

if st.session_state["admin_user"] is None and st.session_state.get("show_login", False):
    _, l_col, _ = st.columns([1, 1, 1])
    with l_col:
        with st.form("login"):
            u, p = st.text_input("Admin ID"), st.text_input("Password", type="password")
            if st.form_submit_button("เข้าสู่ระบบ"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state["admin_user"] = u
                    st.rerun()
                else: st.error("รหัสผิด")

# --- 4. ส่วนหลังบ้าน (Admin Panel) ---
if st.session_state["admin_user"]:
    st.markdown(f"#### 🛡️ จัดการคะแนน (แอดมิน: {st.session_state['admin_user']})")
    f_df = load_main_data()
    
    with st.expander("🎯 ค้นหาชื่อและลงคะแนน", expanded=True):
        s_query = st.text_input("🔍 พิมพ์ชื่อค้นหา")
        s_list = f_df.iloc[:, 0].dropna().tolist()
        f_list = [s for s in s_list if s_query.lower() in str(s).lower()] if s_query else s_list
        
        if f_list:
            sel_n = st.selectbox(f"เลือกนักเรียน ({len(f_list)} คน)", f_list)
            d_cols = [c for c in f_df.columns if "day" in str(c).lower()]
            c1, c2 = st.columns(2)
            with c1: s_day = st.selectbox("เลือกช่อง", d_cols)
            with c2: a_pts = st.number_input("คะแนน", min_value=1, value=5)

            if st.button("🚀 บันทึกคะแนน", use_container_width=True):
                try:
                    idx = f_df[f_df.iloc[:, 0] == sel_n].index[0]
                    f_df.at[idx, s_day] = (pd.to_numeric(f_df.at[idx, s_day], errors='coerce') or 0) + a_pts
                    conn.update(worksheet="Sheet1", data=f_df)
                    st.success("บันทึกเรียบร้อย!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# --- 5. หน้าบ้าน: Leaderboard (Perfect Balance 5 Columns) ---
st.markdown("<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)

try:
    df = load_main_data()
    # ดึง Name(A), Score(AL), EXP(AM), Medal(AN)
    ld = df.iloc[:, [0, 37, 38, 39]].copy()
    ld.columns = ['Name', 'Score', 'EXP', 'Medal']
    ld['Score'] = pd.to_numeric(ld['Score'], errors='coerce').fillna(0)
    
    df_c = ld.copy()
    df_c['Rank'] = df_c['Score'].rank(method='dense', ascending=False).astype(int)
    players = df_c.sort_values(by=['Rank', 'Name']).to_dict('records')

    grid_h = '<div class="leaderboard-grid">'
    for p in players:
        r = p['Rank']
        icon = "👑" if r <= 3 else "🎖️"
        color_class = f"c-{r}" if r <= 3 else ""
        
        grid_h += f"""
        <div class="player-card">
            <div class="rank-tag {color_class}">{icon} #{r}</div>
            <div class="player-name">{p['Name']}</div>
            <div class="score-container">
                <span class="label-score">คะแนนรวม</span>
                <span class="score-num">{p['Score']:.0f}</span>
            </div>
            <div class="card-footer">
                <div class="data-row">
                    <span class="data-label">EXP:</span>
                    <span class="data-val">{p['EXP']}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">ฉายา:</span>
                    <span class="data-val">{p['Medal']}</span>
                </div>
            </div>
        </div>"""
    grid_h += '</div>'
    st.markdown(grid_h, unsafe_allow_html=True)
except Exception as e: 
    st.error(f"กำลังเชื่อมต่อข้อมูล... ({e})")
