import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. การตั้งค่าหน้าเว็บและ CSS (Ultimate Alignment) ---
st.set_page_config(page_title="Patwit Leaderboard", page_icon="👑", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    /* ล้างพื้นที่ว่างขอบจอให้เหลือน้อยที่สุดเพื่อให้พอดี 5 คอลัมน์ */
    [data-testid="block-container"] { padding: 0.5rem 0.2rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; overflow-x: hidden; }

    /* บังคับ 5 คอลัมน์ และล็อกให้ทุกใบสูงเท่ากันด้วย grid-auto-rows */
    .leaderboard-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr) !important;
        grid-auto-rows: 1fr; /* บังคับให้ทุกแถวสูงเท่ากันเป๊ะ */
        gap: 4px;
        width: 100%;
        box-sizing: border-box;
    }

    .player-card {
        background-color: #ffffff;
        border-radius: 4px;
        padding: 5px 2px;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.08);
        border: 1px solid #eee;
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
        height: 100%; /* ยืดให้เต็มช่อง Grid */
        box-sizing: border-box;
    }

    /* ลำดับที่ */
    .rank-tag { font-size: 2.2vw !important; font-weight: 600; opacity: 0.6; line-height: 1; }
    .c-1 { color: #FFD700; } .c-2 { color: #999; } .c-3 { color: #CD7F32; }

    /* ชื่อนักเรียน - ล็อกความสูง 2 บรรทัดเพื่อความสมดุล */
    .player-name {
        font-size: 2.4vw !important;
        font-weight: 600;
        line-height: 1.1;
        height: 5.5vw; 
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin: 3px 0;
        color: #333;
    }
    
    .label-score { font-size: 1.8vw !important; opacity: 0.5; display: block; }
    .score-num { 
        font-size: 4.2vw !important; 
        font-weight: 800; 
        color: #1E88E5;
        line-height: 1;
        margin-bottom: 2px;
    }
    
    .card-footer { 
        border-top: 1px solid #f9f9f9; 
        padding-top: 4px; 
        margin-top: auto;
    }
    
    .data-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        width: 100%;
        margin-bottom: 2px;
    }

    .data-label { font-size: 1.8vw !important; color: #888; margin-top: 1px; }
    
    /* ฉายาชิดขวา และล็อกพื้นที่ 2 บรรทัดเพื่อให้กรอบเท่ากัน */
    .data-val { 
        font-size: 1.8vw !important; 
        font-weight: 600; 
        color: #444; 
        text-align: right; 
        line-height: 1;
        max-width: 65%;
        min-height: 3.8vw; /* ล็อกความสูงขั้นต่ำสำหรับฉายา 2 บรรทัด */
    }

    /* สำหรับหน้าจอคอมพิวเตอร์ */
    @media (min-width: 1024px) {
        [data-testid="block-container"] { padding: 2rem 5rem !important; }
        .leaderboard-grid { gap: 12px; }
        .player-card { min-height: 180px; padding: 12px; }
        .player-name { font-size: 0.95rem !important; height: 38px; }
        .score-num { font-size: 2rem !important; }
        .data-label, .data-val, .label-score, .rank-tag { font-size: 0.75rem !important; }
        .data-val { min-height: 30px; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันจัดการข้อมูล ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(worksheet="Sheet1", ttl="2s")

# --- 3. ระบบ Authentication ---
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
                else: st.error("ข้อมูลไม่ถูกต้อง")

# --- 4. ส่วนหลังบ้าน (Admin) ---
if st.session_state["admin_user"]:
    st.markdown(f"#### 🛡️ แอดมินจัดการคะแนน: {st.session_state['admin_user']}")
    f_df = load_data()
    
    with st.expander("🎯 ลงคะแนนรายบุคคล", expanded=True):
        s_query = st.text_input("🔍 ค้นหาชื่อ")
        s_list = f_df.iloc[:, 0].dropna().tolist()
        f_list = [s for s in s_list if s_query.lower() in str(s).lower()] if s_query else s_list
        
        if f_list:
            sel_n = st.selectbox(f"เลือกนักเรียน ({len(f_list)})", f_list)
            d_cols = [c for c in f_df.columns if "day" in str(c).lower()]
            c1, c2 = st.columns(2)
            with c1: s_day = st.selectbox("เลือกช่อง", d_cols)
            with c2: a_pts = st.number_input("คะแนน", min_value=1, value=5, step=1)

            if st.button("🚀 บันทึก", use_container_width=True):
                try:
                    idx = f_df[f_df.iloc[:, 0] == sel_n].index[0]
                    # จัดการลบทศนิยม
                    curr = pd.to_numeric(f_df.at[idx, s_day], errors='coerce') or 0
                    f_df.at[idx, s_day] = int(curr + a_pts)
                    conn.update(worksheet="Sheet1", data=f_df)
                    st.success("บันทึกแล้ว!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# --- 5. หน้าบ้าน: Leaderboard (Perfect Grid) ---
st.markdown("<h3 style='text-align: center; color: #1E88E5; margin-bottom: 10px;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)

try:
    df = load_data()
    ld = df.iloc[:, [0, 37, 38, 39]].copy()
    ld.columns = ['Name', 'Score', 'EXP', 'Medal']
    
    # ลบทศนิยม
    ld['Score'] = pd.to_numeric(ld['Score'], errors='coerce').fillna(0).astype(int)
    ld['EXP'] = pd.to_numeric(ld['EXP'], errors='coerce').fillna(0).astype(int)
    
    df_c = ld.copy()
    df_c['Rank'] = df_c['Score'].rank(method='dense', ascending=False).astype(int)
    players = df_c.sort_values(by=['Rank', 'Name']).to_dict('records')

    grid_h = '<div class="leaderboard-grid">'
    for p in players:
        r = p['Rank']
        icon = "👑" if r <= 3 else "🎖️"
        color_class = f"c-{r}" if r <= 3 else ""
        
        # จัดการฉายา patwit ให้ขึ้นบรรทัดใหม่
        raw_m = str(p['Medal'])
        formatted_m = raw_m.replace(' ', '<br>', 1) if ' ' in raw_m else raw_m
        
        grid_h += f"""
        <div class="player-card">
            <div class="rank-tag {color_class}">{icon} #{r}</div>
            <div class="player-name">{p['Name']}</div>
            <div>
                <span class="label-score">คะแนนรวม</span>
                <span class="score-num">{p['Score']}</span>
            </div>
            <div class="card-footer">
                <div class="data-row">
                    <span class="data-label">EXP:</span>
                    <span class="data-val">{p['EXP']}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">ฉายา:</span>
                    <span class="data-val">{formatted_m}</span>
                </div>
            </div>
        </div>"""
    grid_h += '</div>'
    st.markdown(grid_h, unsafe_allow_html=True)
except Exception as e: 
    st.info("กำลังโหลด...")
