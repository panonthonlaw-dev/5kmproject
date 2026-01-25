import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. การตั้งค่าหน้าเว็บและ CSS (ล็อก 5 คอลัมน์ตลอดกาล) ---
st.set_page_config(page_title="Patwit Leaderboard", page_icon="👑", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    /* ซ่อนแถบเมนูและ Header ของ Streamlit */
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

    /* บังคับให้เป็น 5 คอลัมน์เสมอ ไม่ว่าหน้าจอจะเล็กแค่ไหน */
    .leaderboard-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr) !important;
        gap: 6px;
        padding: 5px;
    }

    /* ดีไซน์การ์ดผู้เล่นให้กะทัดรัดขึ้น */
    .player-card {
        background-color: var(--secondary-background-color);
        border-radius: 8px;
        padding: 6px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.1);
        min-height: 125px;
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
    }

    /* ตกแต่งสีตามลำดับที่ 1-3 */
    .c-1 { color: #FFD700; } .c-2 { color: #C0C0C0; } .c-3 { color: #CD7F32; }

    .player-name {
        font-size: 0.75em !important;
        font-weight: 600;
        height: 28px;
        overflow: hidden;
        line-height: 1.1;
        margin-top: 4px;
        color: var(--text-color);
    }
    
    .score-num { 
        font-size: 1.1em !important; 
        font-weight: 800; 
        color: var(--primary-color); 
    }
    
    .card-footer { 
        font-size: 0.55em !important; 
        border-top: 1px solid rgba(128, 128, 128, 0.1); 
        padding-top: 3px; 
        opacity: 0.8; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันการจัดการข้อมูล ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_main_data():
    # ดึงข้อมูลจาก Sheet1 (ข้อมูลสด)
    return conn.read(worksheet="Sheet1", ttl="2s")

def load_logs():
    try:
        # ดึงประวัติจาก Logs
        return conn.read(worksheet="Logs", ttl="0s")
    except:
        return pd.DataFrame(columns=['Timestamp', 'Admin', 'Student', 'Day', 'Points', 'Status'])

# --- 3. ระบบ Authentication (Admin Login) ---
if "admin_user" not in st.session_state:
    if "admin_active" in st.query_params:
        st.session_state["admin_user"] = st.query_params.get("user", "Admin")
    else:
        st.session_state["admin_user"] = None

# ปุ่ม Login/Logout มุมขวาบน
h_l, h_r = st.columns([20, 1])
with h_r:
    if st.session_state["admin_user"] is None:
        if st.button("🔓"): st.session_state["show_login"] = not st.session_state.get("show_login", False)
    else:
        if st.button("🚪"): 
            st.session_state["admin_user"] = None
            st.query_params.clear()
            st.rerun()

# ฟอร์ม Login (แสดงเมื่อกด 🔓)
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
    
    with st.expander("🎯 ค้นหาชื่อและลงคะแนน", expanded=True):
        # ระบบค้นหา
        search_q = st.text_input("🔍 พิมพ์ชื่อเพื่อค้นหา", placeholder="เช่น สมชาย, มนตรี...")
        student_list = full_df.iloc[:, 0].dropna().tolist()
        filtered_list = [s for s in student_list if search_q.lower() in str(s).lower()] if search_q else student_list
        
        if not filtered_list:
            st.warning("❌ ไม่พบชื่อนักเรียน")
            sel_name = None
        else:
            sel_name = st.selectbox(f"เลือกนักเรียน ({len(filtered_list)} คน)", filtered_list)

        if sel_name:
            # ข้อมูลสรุปนักเรียน
            row_data = full_df[full_df.iloc[:, 0] == sel_name].iloc[0]
            st.info(f"👤 **{sel_name}** | คะแนนรวม: {row_data.iloc[37]} | {row_data.iloc[39]}")

            # ดึงชื่อคอลัมน์ที่มีคำว่า 'day'
            day_cols = [col for col in full_df.columns if "day" in str(col).lower()]
            
            c1, c2 = st.columns(2)
            with c1:
                sel_day = st.selectbox("เลือกลงช่องคอลัมน์", day_cols) if day_cols else st.error("ไม่พบคอลัมน์ day")
            with c2:
                add_pts = st.number_input("คะแนน", min_value=1, value=5)

            # ตรวจสอบการให้ซ้ำ
            today_s = datetime.now().strftime("%Y-%m-%d")
            already = False
            if not log_df.empty:
                log_df['DOnly'] = pd.to_datetime(log_df['Timestamp']).dt.strftime("%Y-%m-%d")
                check = log_df[(log_df['Student'] == sel_name) & (log_df['Day'] == sel_day) & (log_df['DOnly'] == today_s)]
                if not check.empty: already = True

            if already:
                st.warning(f"⚠️ วันนี้ให้คะแนน {sel_day} ไปแล้ว")
                s_code = st.text_input("รหัสลับเพื่อบันทึกซ้ำ", type="password")

            if st.button("🚀 บันทึกคะแนน", use_container_width=True):
                if already and s_code != st.secrets["admin_secret_code"]["code"]:
                    st.error("รหัสลับผิด")
                elif sel_day:
                    try:
                        r_idx = full_df[full_df.iloc[:, 0] == sel_name].index[0]
                        c_val = full_df.at[r_idx, sel_day]
                        full_df.at[r_idx, sel_day] = (0 if pd.isna(c_val) or c_val == "" else float(c_val)) + add_pts
                        conn.update(worksheet="Sheet1", data=full_df)
                        
                        # บันทึก Log
                        n_log = pd.DataFrame([{
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Admin": st.session_state["admin_user"],
                            "Student": sel_name,
                            "Day": sel_day,
                            "Points": add_pts,
                            "Status": "Edited" if already else "New"
                        }])
                        conn.update(worksheet="Logs", data=pd.concat([log_df, n_log], ignore_index=True).drop(columns=['DOnly'], errors='ignore'))
                        
                        st.success("บันทึกสำเร็จ!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

            # --- แสดง Log เฉพาะคนที่เราเลือก ---
            st.markdown(f"**📜 ประวัติย้อนหลังของ {sel_name}**")
            if not log_df.empty:
                p_logs = log_df[log_df['Student'] == sel_name].sort_values(by="Timestamp", ascending=False)
                if p_logs.empty: st.caption("ยังไม่มีประวัติ")
                else: st.dataframe(p_logs[['Timestamp', 'Day', 'Points', 'Admin']], use_container_width=True)

# --- 5. หน้าบ้าน: Leaderboard (5 Columns) ---
st.markdown("<h2 style='text-align: center;'>🏆 ทำเนียบผู้กล้า</h2>", unsafe_allow_html=True)

try:
    df = load_main_data()
    # ดึง Name(A), Score(AL), EXP(AM), Medal(AN)
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
            <div style="font-size:10px;"><span class="c-{r if r<=3 else 'normal'}">{icon}</span> #{r}</div>
            <div class="player-name">{p['Name']}</div>
            <div><div class="score-num">{p['Score']:.0f}</div></div>
            <div class="card-footer">⚡ {p['EXP']}<br>🏅 {p['Medal']}</div>
        </div>"""
    grid_h += '</div>'
    st.markdown(grid_h, unsafe_allow_html=True)
except: st.info("💡 กำลังดึงข้อมูลล่าสุด...")
