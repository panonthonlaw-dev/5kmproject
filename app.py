import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. การตั้งค่าหน้าเว็บและ CSS (ล็อก 5 คอลัมน์ & สมดุล 100%) ---
st.set_page_config(page_title="Patwit Leaderboard", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    /* ล้างระยะขอบหน้าจอเพื่อให้พอดีกับ 5 คอลัมน์บนมือถือ */
    [data-testid="block-container"] { padding: 0.8rem 0.2rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; overflow-x: hidden; background-color: #f8f9fa; }

    /* บังคับ 5 คอลัมน์ และทุกใบสูงเท่ากัน */
    .leaderboard-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr) !important;
        grid-auto-rows: 1fr;
        gap: 4px;
        width: 100%;
        box-sizing: border-box;
    }

    .player-card {
        background-color: #ffffff;
        border-radius: 6px;
        padding: 8px 3px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #eee;
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
        height: 100%;
    }

    /* ตกแต่ง Rank */
    .rank-tag { font-size: 2.3vw !important; font-weight: 600; opacity: 0.6; line-height: 1; }
    .c-1 { color: #FFD700; } .c-2 { color: #999; } .c-3 { color: #CD7F32; }

    /* ชื่อนักเรียน - ล็อก 2 บรรทัด */
    .player-name {
        font-size: 2.6vw !important;
        font-weight: 600;
        line-height: 1.1;
        height: 5.8vw;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin: 5px 0;
        color: #333;
    }
    
    .label-score { font-size: 1.8vw !important; opacity: 0.5; display: block; margin-top: 3px; }
    .score-num { 
        font-size: 5vw !important; 
        font-weight: 800; 
        color: #1E88E5;
        line-height: 1;
        margin-bottom: 5px;
    }
    
    /* ส่วนท้ายการ์ด: ฉายา Patwit 2 บรรทัดชิดขวา */
    .card-footer { 
        border-top: 1px solid #f5f5f5; 
        padding-top: 6px; 
        margin-top: auto;
    }
    
    .data-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        width: 100%;
        margin-bottom: 2px;
    }

    .data-label { font-size: 1.9vw !important; font-weight: 400; color: #888; margin-top: 2px; }
    
    .data-val { 
        font-size: 2vw !important; 
        font-weight: 600; 
        color: #444; 
        text-align: right; 
        line-height: 1.1;
        max-width: 68%;
    }

    /* สำหรับหน้าจอคอมพิวเตอร์ */
    @media (min-width: 1024px) {
        [data-testid="block-container"] { padding: 2rem 5rem !important; }
        .leaderboard-grid { gap: 12px; }
        .player-card { min-height: 220px; padding: 15px; }
        .player-name { font-size: 1.1rem !important; height: 45px; }
        .score-num { font-size: 2.5rem !important; }
        .data-label, .data-val, .label-score, .rank-tag { font-size: 0.85rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันจัดการข้อมูล (เน้นความสดใหม่ 0s TTL) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name="Sheet1"):
    return conn.read(worksheet=sheet_name, ttl="0s")

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
        with st.form("login_form"):
            u, p = st.text_input("Admin ID"), st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state["admin_user"] = u
                    st.rerun()
                else: st.error("ข้อมูลไม่ถูกต้อง")

# --- 4. ส่วนหลังบ้าน (Admin Panel) ---
if st.session_state["admin_user"]:
    st.markdown(f"#### 🛡️ ระบบจัดการคะแนน (แอดมิน: {st.session_state['admin_user']})")
    f_df = load_data("Sheet1")
    try:
        log_df = load_data("Logs")
    except:
        log_df = pd.DataFrame(columns=['Timestamp', 'Admin', 'Student', 'Day', 'Points', 'Status'])

    with st.expander("🎯 ค้นหาชื่อและลงคะแนน", expanded=True):
        s_query = st.text_input("🔍 ค้นหาชื่อนักเรียน")
        s_list = f_df.iloc[:, 0].dropna().tolist()
        f_list = [s for s in s_list if s_query.lower() in str(s).lower()] if s_query else s_list
        
        if f_list:
            sel_n = st.selectbox(f"เลือกนักเรียน ({len(f_list)} คน)", f_list)
            d_cols = [c for c in f_df.columns if "day" in str(c).lower()]
            c1, c2 = st.columns(2)
            with c1: s_day = st.selectbox("เลือกช่องกิจกรรม", d_cols)
            with c2: a_pts = st.number_input("คะแนน", min_value=1, value=5, step=1)

            # เช็คการบันทึกซ้ำ
            today_s = datetime.now().strftime("%Y-%m-%d")
            already = False
            if not log_df.empty:
                log_df['CheckDate'] = pd.to_datetime(log_df['Timestamp']).dt.strftime("%Y-%m-%d")
                chk = log_df[(log_df['Student'] == sel_n) & (log_df['Day'] == s_day) & (log_df['CheckDate'] == today_s)]
                if not chk.empty: already = True
            
            secret_pass = False
            if already:
                st.warning(f"⚠️ วันนี้บันทึกช่อง {s_day} ของคนนี้ไปแล้ว!")
                sc_code = st.text_input("ระบุรหัสลับเพื่อบันทึกซ้ำ", type="password")
                if sc_code == st.secrets["admin_secret_code"]["code"]: secret_pass = True

            if st.button("🚀 ยืนยันบันทึกคะแนน", use_container_width=True):
                if already and not secret_pass:
                    st.error("รหัสลับผิด!")
                else:
                    try:
                        idx = f_df[f_df.iloc[:, 0] == sel_n].index[0]
                        # คำนวณคะแนนใหม่ (ลบทศนิยม)
                        curr_v = pd.to_numeric(f_df.at[idx, s_day], errors='coerce') or 0
                        f_df.at[idx, s_day] = int(curr_v + a_pts)
                        
                        # --- SAFE SAVE: ส่งไปเฉพาะคอลัมน์ A ถึง AK (Protect AL-AN) ---
                        # คอลัมน์ที่ 0 ถึง 36 คือ A-AK
                        safe_save_df = f_df.iloc[:, :37]
                        conn.update(worksheet="Sheet1", data=safe_save_df)
                        
                        # บันทึก Logs
                        new_log = pd.DataFrame([{
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Admin": st.session_state["admin_user"],
                            "Student": sel_n,
                            "Day": s_day,
                            "Points": a_pts,
                            "Status": "Duplicate/Override" if already else "Success"
                        }])
                        final_logs = pd.concat([log_df.drop(columns=['CheckDate'], errors='ignore'), new_log], ignore_index=True)
                        conn.update(worksheet="Logs", data=final_logs)
                        
                        st.success("บันทึกสำเร็จ!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

            # ประวัติเฉพาะคน (Filter Logs)
            if not log_df.empty:
                st.markdown(f"**📜 ประวัติของ {sel_n}**")
                p_log = log_df[log_df['Student'] == sel_n].sort_values(by="Timestamp", ascending=False)
                st.dataframe(p_log[['Timestamp', 'Day', 'Points', 'Admin', 'Status']], use_container_width=True)

# --- 5. หน้าบ้าน: Leaderboard (Perfect Balance) ---
st.markdown("<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)

try:
    df = load_data("Sheet1")
    # ดึง Name(A), Score(AL), EXP(AM), Medal(AN)
    ld = df.iloc[:, [0, 37, 38, 39]].copy()
    ld.columns = ['Name', 'Score', 'EXP', 'Medal']
    
    # ลบทศนิยม 100%
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
        
        # การจัดการฉายา Patwit 2 บรรทัด
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
    st.info(f"ระบบกำลังเตรียมข้อมูล... ({e})")
