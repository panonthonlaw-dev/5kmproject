import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. การตั้งค่าหน้าเว็บและ CSS (ล็อก 5 คอลัมน์) ---
st.set_page_config(page_title="Patwit Leaderboard", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    [data-testid="block-container"] { padding: 0.8rem 0.2rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body { font-family: 'Sarabun', sans-serif; overflow-x: hidden; }
    .leaderboard-grid { display: grid; grid-template-columns: repeat(5, 1fr) !important; grid-auto-rows: 1fr; gap: 4px; }
    .player-card { background-color: #fff; border-radius: 6px; padding: 8px 3px; text-align: center; border: 1px solid #eee; display: flex; flex-direction: column; justify-content: space-between; height: 100%; }
    .rank-tag { font-size: 2.2vw !important; font-weight: 600; opacity: 0.6; }
    .player-name { font-size: 2.6vw !important; font-weight: 600; line-height: 1.1; height: 5.8vw; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin: 3px 0; }
    .score-num { font-size: 4.8vw !important; font-weight: 800; color: #1E88E5; line-height: 1; }
    .data-row { display: flex; justify-content: space-between; align-items: flex-start; width: 100%; }
    .data-val { font-size: 1.9vw !important; font-weight: 600; color: #444; text-align: right; line-height: 1.1; min-height: 4vw; }
    .c-1 { color: #FFD700; } .c-2 { color: #999; } .c-3 { color: #CD7F32; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. การเชื่อมต่อข้อมูล ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(worksheet="Sheet1", ttl="0s")

# --- 3. ระบบ Admin Login ---
if "admin_user" not in st.session_state: st.session_state["admin_user"] = None

h_l, h_r = st.columns([20, 1])
with h_r:
    if st.session_state["admin_user"] is None:
        if st.button("🔓"): st.session_state["show_login"] = not st.session_state.get("show_login", False)
    else:
        if st.button("🚪"): 
            st.session_state["admin_user"] = None
            st.rerun()

# --- 4. ส่วน Admin Panel (จุดสำคัญ: บันทึกแบบปลอดภัย) ---
if st.session_state["admin_user"]:
    st.markdown(f"#### 🛡️ แอดมินจัดการคะแนน: {st.session_state['admin_user']}")
    f_df = load_data()
    
    with st.expander("🎯 ลงคะแนนรายบุคคล", expanded=True):
        s_query = st.text_input("🔍 พิมพ์ชื่อค้นหา")
        s_list = f_df.iloc[:, 0].dropna().tolist()
        f_list = [s for s in s_list if s_query.lower() in str(s).lower()] if s_query else s_list
        
        if f_list:
            sel_n = st.selectbox(f"เลือกนักเรียน ({len(f_list)} คน)", f_list)
            d_cols = [c for c in f_df.columns if "day" in str(c).lower()]
            c1, c2 = st.columns(2)
            with c1: s_day = st.selectbox("เลือกวันที่", d_cols)
            with c2: a_pts = st.number_input("คะแนน", min_value=1, value=5, step=1)

            if st.button("🚀 ยืนยันบันทึกคะแนน", use_container_width=True):
                try:
                    # ค้นหาแถวนักเรียน
                    idx = f_df[f_df.iloc[:, 0] == sel_n].index[0]
                    # จัดการคะแนนดิบ (เปลี่ยนความว่างเปล่าเป็น 0 แล้วบวกคะแนนใหม่)
                    curr_val = pd.to_numeric(f_df.at[idx, s_day], errors='coerce')
                    f_df.at[idx, s_day] = int((0 if pd.isna(curr_val) else curr_val) + a_pts)
                    
                    # --- [THE KEY] บันทึกเฉพาะคอลัมน์ A ถึง AK (ตำแหน่ง 0 ถึง 36) เท่านั้น ---
                    # วิธีนี้จะทำให้ Google Sheets ไม่ไปยุ่งกับคอลัมน์ AL (37) เป็นต้นไป
                    update_data = f_df.iloc[:, :37]
                    conn.update(worksheet="Sheet1", data=update_data)
                    
                    st.success("บันทึกสำเร็จ! คอลัมน์สูตรปลอดภัยแน่นอน")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# --- 5. หน้าบ้าน: Leaderboard (5 Columns) ---
st.markdown("<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)
try:
    df = load_data()
    # ดึง Name(0), Score(37), EXP(38), Medal(39) มาแสดงผล
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
        raw_m = str(p['Medal'])
        formatted_m = raw_m.replace(' ', '<br>', 1) if ' ' in raw_m else raw_m
        
        grid_h += f"""
        <div class="player-card">
            <div class="rank-tag {color_class}">{icon} #{r}</div>
            <div class="player-name">{p['Name']}</div>
            <div><span class="score-num">{p['Score']}</span><div style="font-size:1.8vw; opacity:0.5;">คะแนนรวม</div></div>
            <div class="card-footer">
                <div class="data-row"><span class="data-label">EXP:</span><span class="data-val">{p['EXP']}</span></div>
                <div class="data-row"><span class="data-label">ฉายา:</span><span class="data-val">{formatted_m}</span></div>
            </div>
        </div>"""
    grid_h += '</div>'
    st.markdown(grid_h, unsafe_allow_html=True)
except Exception as e: st.info(f"ระบบกำลังดึงข้อมูล... ({e})")
