import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าเว็บและซ่อน UI ของระบบ ---
st.set_page_config(page_title="Gaming Leaderboard", page_icon="👑", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

    /* ซ่อนแถบเมนูข้างบนและ Footer ทั้งหมด */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display:none;}
    [data-testid="stHeader"] {display: none;}

    /* การ์ดผู้เล่น */
    .compact-card {
        background-color: var(--secondary-background-color);
        padding: 8px;
        border-radius: 12px;
        margin-bottom: 15px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.1);
        height: 150px;
    }

    /* มงกุฎและอันดับจิ๋ว */
    .rank-header { height: 32px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .crown-icon { font-size: 18px; margin-bottom: -4px; }
    .rank-num-label { font-size: 9px; font-weight: bold; background: rgba(128, 128, 128, 0.1); padding: 0px 5px; border-radius: 10px; }
    .c-1 { color: #FFD700; } .c-2 { color: #C0C0C0; } .c-3 { color: #CD7F32; }
    
    .player-name-text { font-size: 0.9em; font-weight: 600; margin-top: 5px; height: 20px; overflow: hidden; }
    .score-val { font-size: 1.2em; font-weight: 800; color: var(--primary-color); }
    .meta-data { font-size: 0.7em; opacity: 0.7; border-top: 1px solid rgba(128, 128, 128, 0.1); padding-top: 5px; display: flex; justify-content: space-around; }

    /* ปุ่ม Logout จิ๋ว */
    .logout-btn-container { position: fixed; top: 10px; right: 10px; z-index: 999; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ระบบรักษาความปลอดภัย (Login) ---
# ใช้ query_params เพื่อพยายามจำสถานะหลัง Refresh
if "authenticated" not in st.session_state:
    if "logged_in" in st.query_params:
        st.session_state["authenticated"] = True
        st.session_state["username"] = st.query_params.get("user", "Player")
    else:
        st.session_state["authenticated"] = False

def check_password():
    if not st.session_state["authenticated"]:
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            st.write("\n\n\n")
            with st.form("login_form"):
                st.markdown("<h3 style='text-align: center;'>🎮 Player Login</h3>", unsafe_allow_html=True)
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Log In"):
                    if u in st.secrets["users"] and p == st.secrets["users"][u]:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = u
                        # ฝังสถานะไว้ใน URL เผื่อการ Refresh (เบื้องต้น)
                        st.query_params["logged_in"] = "true"
                        st.query_params["user"] = u
                        st.rerun()
                    else: st.error("ข้อมูลไม่ถูกต้อง")
        return False
    return True

# --- 3. การทำงานหลัก ---
if check_password():
    # --- ปุ่ม Logout จิ๋ว มุมขวาบน ---
    col1, col2 = st.columns([15, 1])
    with col2:
        if st.button("🚪", help="ออกจากระบบ"):
            st.session_state["authenticated"] = False
            st.query_params.clear()
            st.rerun()

    st.markdown("<h2 style='text-align: center;'>🏆 ทำเนียบเทพพัฒวิทย์</h2>", unsafe_allow_html=True)

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m")

        if df is not None:
            # ดึงลำดับคอลัมน์ A(0), AL(37), AM(38), AN(39)
            data = df.iloc[:, [0, 37, 38, 39]].copy()
            data.columns = ['Name', 'Score', 'EXP', 'MedalLevel']
            data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
            df_clean = data.dropna(subset=['Score']).copy()

            # อันดับเท่ากันไม่ข้ามเลข (Dense Ranking)
            df_clean['Rank'] = df_clean['Score'].rank(method='dense', ascending=False).astype(int)
            df_sorted = df_clean.sort_values(by='Rank')

            # แสดงผลแบบ Grid 5 ช่อง
            players = df_sorted.to_dict('records')
            for i in range(0, len(players), 5):
                cols = st.columns(5)
                batch = players[i : i+5]
                for idx, player in enumerate(batch):
                    with cols[idx]:
                        r = player['Rank']
                        icon = "👑" if r <= 3 else "🎖️"
                        color = f"c-{r}" if r <= 3 else "c-normal"
                        
                        st.markdown(f"""
                            <div class="compact-card">
                                <div class="rank-header">
                                    <div class="crown-icon {color}">{icon}</div>
                                    <div class="rank-num-label"># {r}</div>
                                </div>
                                <div class="player-name-text">{player['Name']}</div>
                                <div style="font-size: 0.6em; opacity: 0.6;">คะแนนรวม</div>
                                <div class="score-val">{player['Score']:.0f}</div>
                                <div class="meta-data">
                                    <span>⚡ EXP: {player['EXP']}</span>
                                    <span>🏅 {player['MedalLevel']}</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
    except Exception as e:
        st.error("เชื่อมต่อข้อมูลล้มเหลว")
