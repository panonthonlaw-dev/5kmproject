import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าเว็บและซ่อน UI ---
st.set_page_config(page_title="Gaming Leaderboard", page_icon="👑", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

    /* ซ่อนเมนูระบบ */
    header, footer, .stAppDeployButton, [data-testid="stHeader"] { visibility: hidden; display: none; }

    /* สร้างระบบ Grid บังคับหน้าจอ */
    .leaderboard-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr); /* เดสก์ท็อป 5 ช่อง */
        gap: 10px;
        padding: 10px;
    }

    /* ปรับแต่งสำหรับมือถือ (จอเล็กกว่า 600px) */
    @media (max-width: 600px) {
        .leaderboard-grid {
            grid-template-columns: repeat(3, 1fr); /* มือถือบังคับ 3 ช่อง (ถ้า 5 จะเล็กเกินไปอ่านไม่ออก) */
            gap: 5px;
        }
    }

    /* การ์ดผู้เล่น */
    .compact-card {
        background: var(--secondary-background-color);
        border-radius: 10px;
        padding: 8px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.1);
        min-height: 140px;
    }

    .rank-header { height: 30px; margin-bottom: 2px; }
    .crown-icon { font-size: 18px; margin-bottom: -3px; }
    .rank-num-label { font-size: 8px; font-weight: bold; background: rgba(128, 128, 128, 0.1); padding: 0 4px; border-radius: 5px; }
    
    .c-1 { color: #FFD700; } .c-2 { color: #C0C0C0; } .c-3 { color: #CD7F32; }
    .player-name { font-size: 0.8em; font-weight: 600; height: 35px; overflow: hidden; line-height: 1.2; margin: 4px 0; }
    .score-val { font-size: 1.1em; font-weight: 800; color: var(--primary-color); }
    .meta-footer { font-size: 0.6em; opacity: 0.7; border-top: 1px solid rgba(128, 128, 128, 0.1); padding-top: 4px; margin-top: 4px; }

    /* ปุ่ม Logout มุมขวา */
    .logout-container { position: fixed; top: 10px; right: 10px; z-index: 1000; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ระบบ Login และจำสถานะ ---
if "authenticated" not in st.session_state:
    if "logged_in" in st.query_params:
        st.session_state["authenticated"] = True
        st.session_state["username"] = st.query_params.get("user", "Player")
    else: st.session_state["authenticated"] = False

def check_password():
    if not st.session_state["authenticated"]:
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            st.write("\n\n")
            with st.form("login_form"):
                st.markdown("<h3 style='text-align: center;'>🎮 Login</h3>", unsafe_allow_html=True)
                u, p = st.text_input("User"), st.text_input("Pass", type="password")
                if st.form_submit_button("Login"):
                    if u in st.secrets["users"] and p == st.secrets["users"][u]:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = u
                        st.query_params["logged_in"], st.query_params["user"] = "true", u
                        st.rerun()
                    else: st.error("Wrong pass")
        return False
    return True

if check_password():
    # ปุ่ม Logout ขวาบน
    col_l, col_r = st.columns([10, 1])
    with col_r:
        if st.button("🚪"):
            st.session_state["authenticated"] = False
            st.query_params.clear()
            st.rerun()

    st.markdown("<h2 style='text-align: center;'>🏆 Leaderboard</h2>", unsafe_allow_html=True)

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m")
        if df is not None:
            # ดึงข้อมูล AL, AM, AN
            data = df.iloc[:, [0, 37, 38, 39]].copy()
            data.columns = ['Name', 'Score', 'EXP', 'Medal']
            data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
            df_c = data.dropna(subset=['Score']).copy()
            df_c['Rank'] = df_c['Score'].rank(method='dense', ascending=False).astype(int)
            players = df_c.sort_values(by='Rank').to_dict('records')

            # --- ส่วนการสร้าง Grid ด้วย HTML ---
            html_content = '<div class="leaderboard-grid">'
            for p in players:
                r = p['Rank']
                icon = "👑" if r <= 3 else "🎖️"
                color = f"c-{r}" if r <= 3 else "c-normal"
                
                html_content += f"""
                    <div class="compact-card">
                        <div class="rank-header">
                            <div class="crown-icon {color}">{icon}</div>
                            <div class="rank-num-label"># {r}</div>
                        </div>
                        <div class="player-name">{p['Name']}</div>
                        <div style="font-size: 0.55em; opacity: 0.6;">คะแนนรวม</div>
                        <div class="score-val">{p['Score']:.0f}</div>
                        <div class="meta-footer">
                            ⚡ {p['EXP']}<br>🏅 {p['Medal']}
                        </div>
                    </div>
                """
            html_content += '</div>'
            st.markdown(html_content, unsafe_allow_html=True)

    except Exception as e:
        st.error("Error connecting to data")
