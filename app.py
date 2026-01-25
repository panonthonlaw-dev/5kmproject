import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. การตั้งค่าหน้าเว็บและ CSS (หน่วย Scaling ตามหน้าจอจริง) ---
st.set_page_config(page_title="Patwit Leaderboard", page_icon="👑", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

    /* บังคับ 5 คอลัมน์ และใช้หน่วย vw เพื่อให้หดตามขนาดจอ */
    .leaderboard-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr) !important;
        gap: 1vw; /* ระยะห่างปรับตามความกว้างจอ */
        padding: 5px;
        width: 100%;
    }

    .player-card {
        background-color: var(--secondary-background-color);
        border-radius: 5px;
        padding: 1.5vw 1vw;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.1);
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
        aspect-ratio: 1 / 1.4; /* บังคับสัดส่วนการ์ดให้เป็นสี่เหลี่ยมผืนผ้าเท่ากันทุกใบ */
        overflow: hidden;
    }

    /* ใช้หน่วย vw สำหรับฟอนต์เพื่อให้ตัวอักษรเล็กลงอัตโนมัติในมือถือจอเล็ก */
    .rank-text { font-size: 2.2vw !important; opacity: 0.8; }
    .c-1 { color: #FFD700; font-weight: bold; } 
    .c-2 { color: #C0C0C0; font-weight: bold; } 
    .c-3 { color: #CD7F32; font-weight: bold; }

    .player-name {
        font-size: 2.4vw !important; /* ชื่อจะหดตามจอ */
        font-weight: 600;
        line-height: 1.1;
        height: 5.2vw; /* ล็อกความสูงชื่อ */
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin: 2px 0;
    }
    
    .label-text {
        font-size: 1.8vw !important;
        opacity: 0.7;
    }

    .score-num { 
        font-size: 3.5vw !important; /* คะแนนตัวใหญ่ชัดเจน */
        font-weight: 800; 
        color: var(--primary-color);
        line-height: 1;
    }
    
    .card-footer { 
        font-size: 1.8vw !important; 
        border-top: 1px solid rgba(128, 128, 128, 0.1); 
        padding-top: 3px; 
        line-height: 1.2;
        text-align: left;
        white-space: nowrap; /* ป้องกันตัวหนังสือขึ้นบรรทัดใหม่จนเบียดกัน */
    }

    /* สำหรับหน้าจอคอมพิวเตอร์ (จอใหญ่) ให้จำกัดขนาดฟอนต์ไม่ให้ใหญ่เกินไป */
    @media (min-width: 1024px) {
        .player-name { font-size: 0.8em !important; height: 35px; }
        .score-num { font-size: 1.5em !important; }
        .card-footer, .label-text, .rank-text { font-size: 0.6em !important; }
        .player-card { aspect-ratio: auto; min-height: 150px; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันจัดการข้อมูล ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_main_data():
    return conn.read(worksheet="Sheet1", ttl="2s")

def load_logs():
    try:
        return conn.read(worksheet="Logs", ttl="0s")
    except:
        return pd.DataFrame(columns=['Timestamp', 'Admin', 'Student', 'Day', 'Points', 'Status'])

# --- 3. ระบบ Authentication (Admin) ---
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
            u, p = st.text_input("Admin ID"), st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                if u in st.secrets["users"] and p == st.secrets["users"][u]:
                    st.session_state["admin_user"] = u
                    st.query_params["admin_active"], st.query_params["user"] = "true", u
                    st.session_state["show_login"] = False
                    st.rerun()
                else: st.error("รหัสผ่านไม่ถูกต้อง")

# --- 4. ส่วนหลังบ้าน (Admin Panel) ---
if st.session_state["admin_user"]:
    st.markdown(f"### 🛡️ จัดการคะแนน (Admin: {st.session_state['admin_user']})")
    f_df = load_main_data()
    l_df = load_logs()
    
    with st.expander("🎯 ค้นหาและให้คะแนนรายบุคคล", expanded=True):
        s_query = st.text_input("🔍 พิมพ์ชื่อเพื่อค้นหา")
        s_list = f_df.iloc[:, 0].dropna().tolist()
        f_list = [s for s in s_list if s_query.lower() in str(s).lower()] if s_query else s_list
        
        if not f_list:
            st.warning("ไม่พบชื่อ")
            sel_n = None
        else:
            sel_n = st.selectbox(f"เลือกนักเรียน ({len(f_list)} คน)", f_list)

        if sel_n:
            r_data = f_df[f_df.iloc[:, 0] == sel_n].iloc[0]
            st.info(f"👤 **{sel_n}** | คะแนนรวม: {r_data.iloc[37]} | {r_data.iloc[39]}")

            d_cols = [c for c in f_df.columns if "day" in str(c).lower()]
            c1, c2 = st.columns(2)
            with c1: s_day = st.selectbox("เลือกช่อง", d_cols)
            with c2: a_pts = st.number_input("คะแนน", min_value=1, value=5)

            t_s = datetime.now().strftime("%Y-%m-%d")
            already = False
            if not l_df.empty:
                l_df['DOnly'] = pd.to_datetime(l_df['Timestamp']).dt.strftime("%Y-%m-%d")
                chk = l_df[(l_df['Student'] == sel_n) & (l_df['Day'] == s_day) & (l_df['DOnly'] == t_s)]
                if not chk.empty: already = True

            if already:
                st.warning("⚠️ วันนี้เคยให้คะแนนช่องนี้ไปแล้ว")
                sc_code = st.text_input("รหัสลับบันทึกซ้ำ", type="password")

            if st.button("🚀 บันทึกคะแนน", use_container_width=True):
                if already and sc_code != st.secrets["admin_secret_code"]["code"]:
                    st.error("รหัสลับผิด")
                else:
                    try:
                        idx = f_df[f_df.iloc[:, 0] == sel_n].index[0]
                        f_df.at[idx, s_day] = (0 if pd.isna(f_df.at[idx, s_day]) or f_df.at[idx, s_day] == "" else float(f_df.at[idx, s_day])) + a_pts
                        conn.update(worksheet="Sheet1", data=f_df)
                        
                        nl = pd.DataFrame([{"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Admin": st.session_state["admin_user"], "Student": sel_n, "Day": s_day, "Points": a_pts, "Status": "New"}])
                        conn.update(worksheet="Logs", data=pd.concat([l_df, nl], ignore_index=True).drop(columns=['DOnly'], errors='ignore'))
                        st.success("บันทึกสำเร็จ!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

            st.markdown(f"**📜 ประวัติของ {sel_n}**")
            if not l_df.empty:
                p_logs = l_df[l_df['Student'] == sel_n].sort_values(by="Timestamp", ascending=False)
                st.dataframe(p_logs[['Timestamp', 'Day', 'Points', 'Admin']], use_container_width=True)

# --- 5. หน้าบ้าน: Leaderboard (Perfect Balance) ---
st.markdown("<h3 style='text-align: center;'>🏆 ทำเนียบผู้กล้า</h3>", unsafe_allow_html=True)

try:
    df = load_main_data()
    ld = df.iloc[:, [0, 37, 38, 39]].copy()
    ld.columns = ['Name', 'Score', 'EXP', 'Medal']
    ld['Score'] = pd.to_numeric(ld['Score'], errors='coerce')
    
    df_c = ld.dropna(subset=['Score']).copy()
    df_c['Rank'] = df_c['Score'].rank(method='dense', ascending=False).astype(int)
    players = df_c.sort_values(by='Rank').to_dict('records')

    grid_h = '<div class="leaderboard-grid">'
    for p in players:
        r = p['Rank']
        icon = "👑" if r <= 3 else "🎖️"
        grid_h += f"""
        <div class="player-card">
            <div class="rank-text"><span class="c-{r if r<=3 else 'normal'}">{icon}</span> #{r}</div>
            <div class="player-name">{p['Name']}</div>
            <div>
                <div class="label-text">คะแนนรวม</div>
                <div class="score-num">{p['Score']:.0f}</div>
            </div>
            <div class="card-footer">
                <div><b>EXP:</b> {p['EXP']}</div>
                <div><b>ฉายา:</b> {p['Medal']}</div>
            </div>
        </div>"""
    grid_h += '</div>'
    st.markdown(grid_h, unsafe_allow_html=True)
except: st.info("💡 กำลังดึงข้อมูลล่าสุด...")
