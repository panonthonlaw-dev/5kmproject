import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Patwit Leaderboard", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    [data-testid="block-container"] { padding: 0.8rem 0.2rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body { font-family: 'Sarabun', sans-serif; overflow-x: hidden; background-color: #f8f9fa; }
    .leaderboard-grid { display: grid; grid-template-columns: repeat(5, 1fr) !important; grid-auto-rows: 1fr; gap: 4px; width: 100%; box-sizing: border-box; }
    .player-card { background-color: #ffffff; border-radius: 6px; padding: 8px 3px; text-align: center; border: 1px solid #eee; display: flex; flex-direction: column; justify-content: space-between; height: 100%; }
    .rank-tag { font-size: 2.2vw !important; font-weight: 600; opacity: 0.6; }
    .c-1 { color: #FFD700; } .c-2 { color: #999; } .c-3 { color: #CD7F32; }
    .player-name { font-size: 2.5vw !important; font-weight: 600; line-height: 1.1; height: 5.5vw; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin: 4px 0; color: #333; }
    .score-num { font-size: 4.8vw !important; font-weight: 800; color: #1E88E5; line-height: 1; }
    .data-row { display: flex; justify-content: space-between; align-items: flex-start; width: 100%; margin-bottom: 2px; }
    .data-val { font-size: 1.9vw !important; font-weight: 600; color: #444; text-align: right; line-height: 1.1; min-height: 3.8vw; }
    @media (min-width: 1024px) { .player-card { min-height: 200px; padding: 15px; } .player-name { font-size: 1rem !important; height: 40px; } .score-num { font-size: 2.2rem !important; } .data-val { font-size: 0.8rem !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- 2. การเชื่อมต่อข้อมูล ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_fresh_data():
    # บังคับอ่านข้อมูลใหม่ล่าสุดจาก Sheets เสมอ
    return conn.read(worksheet="Sheet1", ttl="0s")

# --- 3. ระบบ Authentication ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

h_l, h_r = st.columns([20, 1])
with h_r:
    if not st.session_state.logged_in:
        if st.button("🔓"): st.session_state.show_login = not st.session_state.get("show_login", False)
    else:
        if st.button("🚪"): 
            st.session_state.logged_in = False
            st.rerun()

if not st.session_state.logged_in and st.session_state.get("show_login", False):
    _, l_col, _ = st.columns([1, 1, 1])
    with l_col:
        with st.form("admin_login"):
            u = st.text_input("Admin ID")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("เข้าสู่ระบบ"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state.logged_in = True
                    st.session_state.admin_name = u
                    st.rerun()
                else: st.error("ข้อมูลไม่ถูกต้อง")

# --- 4. ส่วนแอดมิน (ป้องกันการย้อนเวอร์ชัน) ---
if st.session_state.logged_in:
    st.markdown(f"#### 🛡️ แอดมินจัดการคะแนน: {st.session_state.admin_name}")
    
    # ดึงข้อมูลมาแสดงตัวเลือก
    admin_df = load_fresh_data()
    
    with st.expander("🎯 บันทึกคะแนน", expanded=True):
        s_query = st.text_input("🔍 ค้นหาชื่อ")
        s_list = admin_df.iloc[:, 0].dropna().tolist()
        f_list = [s for s in s_list if s_query.lower() in str(s).lower()] if s_query else s_list
        
        if f_list:
            sel_n = st.selectbox(f"เลือกนักเรียน ({len(f_list)} คน)", f_list)
            d_cols = [c for c in admin_df.columns if "day" in str(c).lower()]
            c1, c2 = st.columns(2)
            with c1: s_day = st.selectbox("กิจกรรม", d_cols)
            with c2: a_pts = st.number_input("คะแนน", min_value=1, value=5, step=1)

            if st.button("🚀 ยืนยันบันทึกคะแนน", use_container_width=True):
                try:
                    # --- ขั้นตอนป้องกันการย้อนเวอร์ชัน ---
                    # 1. ล้าง Cache ทั้งหมดก่อนเริ่มกระบวนการ
                    st.cache_data.clear()
                    
                    # 2. อ่านข้อมูล 'สด' ใหม่อีกครั้งทันทีที่กดปุ่ม เพื่อให้ได้เวอร์ชันล่าสุดจริงๆ
                    fresh_df = conn.read(worksheet="Sheet1", ttl="0s")
                    
                    # 3. แก้ไขเฉพาะในช่องที่ต้องการ (F ถึง AK เท่านั้น)
                    idx = fresh_df[fresh_df.iloc[:, 0] == sel_n].index[0]
                    curr_val = pd.to_numeric(fresh_df.at[idx, s_day], errors='coerce')
                    fresh_df.at[idx, s_day] = int((0 if pd.isna(curr_val) else curr_val) + a_pts)
                    
                    # 4. บันทึกกลับไปเฉพาะคอลัมน์ A ถึง AK (ตำแหน่ง 0-36)
                    # การส่งไปแค่ช่วงนี้ จะไม่ไปเขียนทับคอลัมน์ AL-AN ใน Sheets
                    data_to_save = fresh_df.iloc[:, :37]
                    conn.update(worksheet="Sheet1", data=data_to_save)
                    
                    st.success("บันทึกสำเร็จ!")
                    # 5. ล้าง Cache อีกครั้งหลังบันทึกเสร็จ เพื่อให้หน้า Leaderboard โหลดใหม่
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

# --- 5. หน้าแสดงผล (Leaderboard) ---
st.markdown("<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)
try:
    # หน้าจอทั่วไปใช้ cache สั้นๆ เพื่อความเร็ว แต่หน้าแอดมินใช้ข้อมูลสดเสมอ
    display_df = load_fresh_data()
    ld = display_df.iloc[:, [0, 37, 38, 39]].copy()
    ld.columns = ['Name', 'Score', 'EXP', 'Medal']
    
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
        grid_h += f'<div class="player-card"><div class="rank-tag {color_class}">{icon} #{r}</div><div class="player-name">{p["Name"]}</div><div><span class="score-num">{p["Score"]}</span><div style="font-size:1.8vw; opacity:0.5;">คะแนนรวม</div></div><div class="card-footer"><div class="data-row"><span class="data-label">EXP:</span><span class="data-val">{p["EXP"]}</span></div><div class="data-row"><span class="data-label">ฉายา:</span><span class="data-val">{formatted_m}</span></div></div></div>'
    grid_h += '</div>'
    st.markdown(grid_h, unsafe_allow_html=True)
except Exception as e:
    st.info("กำลังโหลดข้อมูล...")
