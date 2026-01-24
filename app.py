import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Gaming Leaderboard", page_icon="👑", layout="wide")

# --- 2. CSS บังคับให้เป็น Grid และซ่อนเมนูระบบ ---
# ส่วนนี้สำคัญมาก ต้องใช้ unsafe_allow_html=True เพื่อไม่ให้มันโชว์เป็นโค้ดดิบ
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    /* ซ่อนเมนูและส่วนหัวของ Streamlit */
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { 
        visibility: hidden; 
        display: none; 
    }

    /* บังคับฟอนต์ทั้งแอป */
    html, body, [class*="css"] { 
        font-family: 'Sarabun', sans-serif; 
    }

    /* ระบบ Grid บังคับหน้าจอ */
    .leaderboard-container {
        display: grid;
        grid-template-columns: repeat(5, 1fr); /* 5 ช่องในคอม */
        gap: 12px;
        padding: 10px;
    }

    /* ปรับแต่งสำหรับมือถือ (จอเล็กกว่า 768px) */
    @media (max-width: 768px) {
        .leaderboard-container {
            grid-template-columns: repeat(3, 1fr); /* 3 ช่องในมือถือ เพื่อให้อ่านออก */
            gap: 8px;
        }
    }

    /* การ์ดผู้เล่นแบบ Compact */
    .player-box {
        background-color: var(--secondary-background-color);
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.1);
        min-height: 150px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .crown-zone { height: 35px; }
    .crown-img { font-size: 20px; line-height: 1; }
    .rank-tag { font-size: 9px; font-weight: bold; opacity: 0.7; }

    .c-1 { color: #FFD700; } /* ทอง */
    .c-2 { color: #C0C0C0; } /* เงิน */
    .c-3 { color: #CD7F32; } /* ทองแดง */

    .p-name { font-size: 0.9em; font-weight: 600; margin: 5px 0; height: 35px; overflow: hidden; line-height: 1.2; }
    .score-label { font-size: 0.6em; opacity: 0.6; text-transform: uppercase; }
    .score-big { font-size: 1.3em; font-weight: 800; color: var(--primary-color); margin-bottom: 5px; }
    
    .stats-footer { 
        font-size: 0.65em; 
        border-top: 1px solid rgba(128, 128, 128, 0.1); 
        padding-top: 5px; 
        opacity: 0.8;
    }

    /* ปุ่ม Logout ขวาบน */
    .top-right {
        position: absolute;
        top: 10px;
        right: 10px;
        z-index: 9999;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ระบบ Login พร้อมจำสถานะ Refresh ---
if "authenticated" not in st.session_state:
    # เช็คจาก URL เผื่อมีการ Refresh
    if "logged_in" in st.query_params:
        st.session_state["authenticated"] = True
        st.session_state["username"] = st.query_params.get("user", "Player")
    else:
        st.session_state["authenticated"] = False

def check_auth():
    if not st.session_state["authenticated"]:
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            st.write("\n\n\n")
            with st.form("login"):
                st.markdown("<h3 style='text-align: center;'>🎮 Player Login</h3>", unsafe_allow_html=True)
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Log In"):
                    if u in st.secrets["users"] and p == st.secrets["users"][u]:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = u
                        st.query_params["logged_in"] = "true"
                        st.query_params["user"] = u
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        return False
    return True

# --- 4. การทำงานหลักเมื่อ Login แล้ว ---
if check_auth():
    # สร้างปุ่ม Logout เล็กๆ มุมขวา
    l_col, r_col = st.columns([20, 1])
    with r_col:
        if st.button("🚪"):
            st.session_state["authenticated"] = False
            st.query_params.clear()
            st.rerun()

    st.markdown("<h2 style='text-align: center;'>🏆 ทำเนียบผู้กล้า</h2>", unsafe_allow_html=True)

    try:
        # ดึงข้อมูลจาก Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m")

        if df is not None:
            # ดึงคอลัมน์ A(0), AL(37), AM(38), AN(39)
            data = df.iloc[:, [0, 37, 38, 39]].copy()
            data.columns = ['Name', 'Score', 'EXP', 'Medal']
            data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
            
            # คำนวณอันดับแบบไม่ข้ามเลข (Dense Ranking)
            df_clean = data.dropna(subset=['Score']).copy()
            df_clean['Rank'] = df_clean['Score'].rank(method='dense', ascending=False).astype(int)
            players = df_clean.sort_values(by='Rank').to_dict('records')

            # --- เริ่มสร้าง HTML Grid ---
            grid_html = '<div class="leaderboard-container">'
            
            for p in players:
                r = p['Rank']
                # เลือกสีมงกุฎ
                c_class = f"c-{r}" if r <= 3 else ""
                icon = "👑" if r <= 3 else "🎖️"
                
                # ประกอบการ์ดแต่ละใบ
                grid_html += f"""
                <div class="player-box">
                    <div class="crown-zone">
                        <div class="crown-img {c_class}">{icon}</div>
                        <div class="rank-tag">RANK {r}</div>
                    </div>
                    <div class="p-name">{p['Name']}</div>
                    <div>
                        <div class="score-label">คะแนนรวม</div>
                        <div class="score-big">{p['Score']:.0f}</div>
                    </div>
                    <div class="stats-footer">
                        ⚡ EXP: {p['EXP']}<br>🏅 ระดับเหรียญ: {p['Medal']}
                    </div>
                </div>
                """
            
            grid_html += '</div>'
            
            # แสดงผล HTML ทั้งหมด
            st.markdown(grid_html, unsafe_allow_html=True)

    except Exception as e:
        st.error("เชื่อมต่อข้อมูล Google Sheets ไม่ได้ ตรวจสอบ URL ใน Secrets")
