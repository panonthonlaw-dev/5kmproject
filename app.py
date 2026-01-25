import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. การตั้งค่าหน้าเว็บและ CSS (Ultimate Professional Grid) ---
st.set_page_config(page_title="Patwit Leaderboard", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    [data-testid="block-container"] { padding: 0.5rem 0.2rem !important; }
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; overflow-x: hidden; background-color: #fcfcfc; }

    /* บังคับ 5 คอลัมน์ และล็อกให้ทุกใบสูงเท่ากันเป๊ะ */
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
        border-radius: 4px;
        padding: 5px 2px;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.08);
        border: 1px solid #eee;
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
        height: 100%;
        box-sizing: border-box;
    }

    .rank-tag { font-size: 2.2vw !important; font-weight: 600; opacity: 0.6; line-height: 1; }
    .c-1 { color: #FFD700; } .c-2 { color: #999; } .c-3 { color: #CD7F32; }

    .player-name {
        font-size: 2.6vw !important;
        font-weight: 600;
        line-height: 1.1;
        height: 5.8vw; 
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin: 3px 0;
        color: #333;
    }
    
    .label-score { font-size: 1.8vw !important; opacity: 0.5; display: block; }
    .score-num { 
        font-size: 4.8vw !important; 
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
    
    /* ฉายาชิดขวา และล็อกพื้นที่ขั้นต่ำ */
    .data-val { 
        font-size: 1.9vw !important; 
        font-weight: 600; 
        color: #444; 
        text-align: right; 
        line-height: 1.1;
        max-width: 65%;
        min-height: 4vw; 
    }

    @media (min-width: 1024px) {
        [data-testid="block-container"] { padding: 2rem 5rem !important; }
        .leaderboard-grid { gap: 12px; }
        .player-card { min-height: 200px; padding: 12px; }
        .player-name { font-size: 1.1rem !important; height: 45px; }
        .score-num { font-size: 2.2rem !important; }
        .data-label, .data-val, .label-score, .rank-tag { font-size: 0.8rem !important; }
        .data-val { min-height: 35px; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. การเชื่อมต่อข้อมูล (Safe Data Loading) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name="Sheet1"):
    # อ่านข้อมูลสดใหม่ทุกลมหายใจด้วย ttl=0
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
        with st.form("admin_login"):
            u, p = st.text_input("Admin ID"), st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state["admin_user"] = u
                    st.rerun()
                else: st.error("ข้อมูลไม่ถูกต้อง")

# --- 4. ส่วนหลังบ้าน (Admin: แก้ไขปัญหา NaN และ ปกป้องสูตร) ---
if st.session_state["admin_user"]:
    st.markdown(f"#### 🛡️ แอดมิน: {st.session_state['admin_user']}")
    f_df = load_data("Sheet1")
    try:
        log_df = load_data("Logs")
    except:
        log_df = pd.DataFrame(columns=['Timestamp', 'Admin', 'Student', 'Day', 'Points', 'Status'])

    with st.expander("🎯 ลงคะแนนรายบุคคล", expanded=True):
        s_query = st.text_input("🔍 ค้นชื่อนักเรียน")
        s_list = f_df.iloc[:, 0].dropna().tolist()
        f_list = [s for s in s_list if s_query.lower() in str(s).lower()] if s_query else s_list
        
        if f_list:
            sel_n = st.selectbox(f"เลือกนักเรียน ({len(f_list)})", f_list)
            d_cols = [c for c in f_df.columns if "day" in str(c).lower()]
            c1, c2 = st.columns(2)
            with c1: s_day = st.selectbox("กิจกรรม", d_cols)
            with c2: a_pts = st.number_input("คะแนน", min_value=1, value=5, step=1)

            # ตรวจสอบการบันทึกซ้ำ
            today_s = datetime.now().strftime("%Y-%m-%d")
            already = False
            if not log_df.empty:
                log_df['CheckDate'] = pd.to_datetime(log_df['Timestamp']).dt.strftime("%Y-%m-%d")
                chk = log_df[(log_df['Student'].astype(str) == str(sel_n)) & (log_df['Day'].astype(str) == str(s_day)) & (log_df['CheckDate'] == today_s)]
                if not chk.empty: already = True
            
            secret_pass = False
            if already:
                st.warning(f"⚠️ วันนี้ลงคะแนนช่อง {s_day} ให้ {sel_n} ไปแล้ว")
                sc_code = st.text_input("รหัสลับบันทึกซ้ำ", type="password")
                if sc_code == st.secrets["admin_secret_code"]["code"]: secret_pass = True

            if st.button("🚀 บันทึกคะแนน", use_container_width=True):
                if already and not secret_pass:
                    st.error("รหัสลับไม่ถูกต้อง")
                else:
                    try:
                        idx = f_df[f_df.iloc[:, 0] == sel_n].index[0]
                        # แก้ปัญหา NaN: แปลงค่าเดิมเป็นตัวเลข ถ้าว่างให้เป็น 0
                        raw_v = pd.to_numeric(f_df.at[idx, s_day], errors='coerce')
                        curr_v = 0 if pd.isna(raw_v) else raw_v
                        f_df.at[idx, s_day] = int(curr_v + a_pts)
                        
                        # --- SAFE UPDATE: ส่งกลับไปแค่คอลัมน์ A ถึง AK เท่านั้น ---
                        # เพื่อไม่ให้แอปไปเขียนทับคอลัมน์ AL, AM, AN ที่มีสูตรอยู่
                        safe_df = f_df.iloc[:, :37] 
                        conn.update(worksheet="Sheet1", data=safe_df)
                        
                        # บันทึก Logs
                        n_log = pd.DataFrame([{
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Admin": st.session_state["admin_user"],
                            "Student": sel_n, "Day": s_day, "Points": a_pts,
                            "Status": "Override" if already else "Success"
                        }])
                        final_log = pd.concat([log_df.drop(columns=['CheckDate'], errors='ignore'), n_log], ignore_index=True)
                        conn.update(worksheet="Logs", data=final_log)
                        
                        st.success(f"บันทึกสำเร็จ! สูตรใน Sheets ปลอดภัยแน่นอน")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

            if not log_df.empty:
                st.markdown(f"**📜 ประวัติของ {sel_n}**")
                st.dataframe(log_df[log_df['Student'] == sel_n].sort_values(by="Timestamp", ascending=False), use_container_width=True)

# --- 5. หน้าบ้าน: Leaderboard (Perfect 5-Columns & No Decimals) ---
st.markdown("<h3 style='text-align: center; color: #1E88E5;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)

try:
    df = load_data("Sheet1")
    # ดึง Name(A), Score(AL), EXP(AM), Medal(AN)
    ld = df.iloc[:, [0, 37, 38, 39]].copy()
    ld.columns = ['Name', 'Score', 'EXP', 'Medal']
    
    # แก้ปัญหา NaN และลบทศนิยมออก (astype int)
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
        
        # จัดการฉายา patwit ให้ขึ้นบรรทัดใหม่และชิดขวา
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
    st.info(f"ระบบกำลังโหลดข้อมูลสดจาก Sheets... ({e})")
