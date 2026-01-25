import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. การตั้งค่าหน้าเว็บและ CSS (เน้นอ่านง่ายบนมือถือ) ---
st.set_page_config(page_title="Patwit Leaderboard", page_icon="👑", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

    .leaderboard-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr) !important;
        gap: 5px;
        padding: 5px;
    }

    .player-card {
        background-color: var(--secondary-background-color);
        border-radius: 8px;
        padding: 5px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.1);
        min-height: 140px;
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
    }

    .c-1 { color: #FFD700; } .c-2 { color: #C0C0C0; } .c-3 { color: #CD7F32; }

    .player-name {
        font-size: 0.7em !important;
        font-weight: 600;
        height: 24px;
        overflow: hidden;
        line-height: 1.1;
        margin-bottom: 2px;
    }
    
    .label-text {
        font-size: 0.5em !important;
        opacity: 0.7;
        margin-bottom: -2px;
    }

    .score-num { 
        font-size: 1em !important; 
        font-weight: 800; 
        color: var(--primary-color);
        margin-bottom: 2px;
    }
    
    .card-footer { 
        font-size: 0.5em !important; 
        border-top: 1px solid rgba(128, 128, 128, 0.1); 
        padding-top: 3px; 
        line-height: 1.2;
        text-align: left;
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
                else: st.error("ข้อมูลไม่ถูกต้อง")

# --- 4. ส่วนหลังบ้าน (Admin Panel) ---
if st.session_state["admin_user"]:
    st.markdown(f"### 🛡️ จัดการคะแนน (Admin: {st.session_state['admin_user']})")
    full_df = load_main_data()
    log_df = load_logs()
    
    with st.expander("🎯 ค้นหาและลงคะแนนรายบุคคล", expanded=True):
        search_q = st.text_input("🔍 พิมพ์ชื่อเพื่อค้นหา")
        student_list = full_df.iloc[:, 0].dropna().tolist()
        filtered_list = [s for s in student_list if search_q.lower() in str(s).lower()] if search_q else student_list
        
        if not filtered_list:
            st.warning("ไม่พบชื่อ")
            sel_name = None
        else:
            sel_name = st.selectbox(f"เลือกนักเรียน ({len(filtered_list)} คน)", filtered_list)

        if sel_name:
            row_data = full_df[full_df.iloc[:, 0] == sel_name].iloc[0]
            st.info(f"👤 **{sel_name}** | คะแนน: {row_data.iloc[37]} | {row_data.iloc[39]}")

            day_cols = [col for col in full_df.columns if "day" in str(col).lower()]
            c1, c2 = st.columns(2)
            with c1: sel_day = st.selectbox("เลือกช่อง", day_cols)
            with c2: add_pts = st.number_input("คะแนน", min_value=1, value=5)

            today_s = datetime.now().strftime("%Y-%m-%d")
            already = False
            if not log_df.empty:
                log_df['DOnly'] = pd.to_datetime(log_df['Timestamp']).dt.strftime("%Y-%m-%d")
                check = log_df[(log_df['Student'] == sel_name) & (log_df['Day'] == sel_day) & (log_df['DOnly'] == today_s)]
                if not check.empty: already = True

            if already:
                st.warning("⚠️ วันนี้เคยให้คะแนนช่องนี้ไปแล้ว")
                s_code = st.text_input("รหัสลับบันทึกซ้ำ", type="password")

            if st.button("🚀 บันทึกคะแนน", use_container_width=True):
                if already and s_code != st.secrets["admin_secret_code"]["code"]:
                    st.error("รหัสลับผิด")
                else:
                    try:
                        r_idx = full_df[full_df.iloc[:, 0] == sel_name].index[0]
                        c_val = full_df.at[r_idx, sel_day]
                        full_df.at[r_idx, sel_day] = (0 if pd.isna(c_val) or c_val == "" else float(c_val)) + add_pts
                        conn.update(worksheet="Sheet1", data=full_df)
                        
                        n_log = pd.DataFrame([{"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Admin": st.session_state["admin_user"], "Student": sel_name, "Day": sel_day, "Points": add_pts, "Status": "New"}])
                        conn.update(worksheet="Logs", data=pd.concat([log_df, n_log], ignore_index=True).drop(columns=['DOnly'], errors='ignore'))
                        st.success("สำเร็จ!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

            st.markdown(f"**📜 ประวัติของ {sel_name}**")
            if not log_df.empty:
                p_logs = log_df[log_df['Student'] == sel_name].sort_values(by="Timestamp", ascending=False)
                st.dataframe(p_logs[['Timestamp', 'Day', 'Points', 'Admin']], use_container_width=True)

# --- 5. หน้าบ้าน: Leaderboard (5 Columns พร้อมป้ายกำกับ) ---
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
            <div style="font-size:9px;"><span class="c-{r if r<=3 else 'normal'}">{icon}</span> #{r}</div>
            <div class="player-name">{p['Name']}</div>
            <div>
                <div class="label-text">คะแนนรวม</div>
                <div class="score-num">{p['Score']:.0f}</div>
            </div>
            <div class="card-footer">
                <div><b>EXP:</b> {p['EXP']}</div>
                <div style="margin-top:2px;"><b>ฉายา:</b> {p['Medal']}</div>
            </div>
        </div>"""
    grid_h += '</div>'
    st.markdown(grid_h, unsafe_allow_html=True)
except: st.info("💡 กำลังโหลดข้อมูล...")
