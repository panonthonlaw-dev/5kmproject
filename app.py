import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าเว็บ (Wide Layout) ---
st.set_page_config(page_title="Gaming Leaderboard", page_icon="👑", layout="wide")

# --- 2. Custom CSS: ปรับโฉมเป็นมงกุฎและย่อขนาดช่องอันดับ ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; background-color: #f8f9fa; }

    /* การ์ดผู้เล่นแบบเล็กพิเศษ */
    .compact-card {
        background: white;
        padding: 10px;
        border-radius: 12px;
        margin-bottom: 15px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        height: 160px;
        position: relative;
    }

    /* ส่วนมงกุฎและอันดับ (จิ๋ว) */
    .rank-section {
        height: 40px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-bottom: 5px;
    }
    .crown {
        font-size: 24px;
        line-height: 1;
        margin-bottom: -5px;
    }
    .rank-number {
        font-size: 10px;
        font-weight: bold;
        background: rgba(0,0,0,0.1);
        padding: 1px 5px;
        border-radius: 10px;
        color: #444;
    }
    
    /* สีมงกุฎ */
    .crown-1 { color: #FFD700; text-shadow: 0 0 5px rgba(255,215,0,0.5); } /* ทอง */
    .crown-2 { color: #C0C0C0; text-shadow: 0 0 5px rgba(192,192,192,0.5); } /* เงิน */
    .crown-3 { color: #CD7F32; text-shadow: 0 0 5px rgba(205,127,50,0.5); } /* ทองแดง */
    .crown-normal { color: #dee2e6; font-size: 18px; } /* อันดับทั่วไป */

    /* รายละเอียดข้อความ */
    .name-text { font-size: 0.9em; font-weight: 600; color: #333; height: 25px; overflow: hidden; margin-bottom: 5px; }
    .score-label { color: #888; font-size: 0.7em; margin-bottom: 0px; text-transform: uppercase; }
    .score-value { font-size: 1.2em; font-weight: 800; color: #2e3131; margin-bottom: 5px; }
    .exp-coin-text { font-size: 0.7em; color: #6c757d; border-top: 1px solid #f0f0f0; padding-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ระบบ Login ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        _, col, _ = st.columns([1, 1, 1])
        with col:
            with st.form("login"):
                st.subheader("🎮 Player Login")
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Log In"):
                    if u in st.secrets["users"] and p == st.secrets["users"][u]:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = u
                        st.rerun()
                    else: st.error("ข้อมูลไม่ถูกต้อง")
        return False
    return True

if check_password():
    st.markdown("<h2 style='text-align: center;'>🏆 ทำเนียบผู้กล้า</h2>", unsafe_allow_html=True)

    try:
        # 1. ดึงข้อมูลจาก Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m")

        if df is not None:
            # 2. จัดเตรียมข้อมูล (A, AL, AM, AN)
            data = df.iloc[:, [0, 37, 38, 39]].copy()
            data.columns = ['Name', 'Score', 'EXP', 'Coin']
            
            data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
            df_clean = data.dropna(subset=['Score']).copy()

            # ใช้ Dense Ranking (1, 1, 2, 2, 3...)
            df_clean['Rank'] = df_clean['Score'].rank(method='dense', ascending=False).astype(int)
            df_sorted = df_clean.sort_values(by='Rank')

            # 3. แสดงผลแบบ Grid (5 ช่องต่อแถว)
            players = df_sorted.to_dict('records')
            for i in range(0, len(players), 5):
                cols = st.columns(5)
                batch = players[i:i+5]
                
                for idx, player in enumerate(batch):
                    with cols[idx]:
                        rank = player['Rank']
                        
                        # เลือกมงกุฎตามอันดับ
                        if rank == 1:
                            crown_html = f'<div class="crown crown-1">👑</div>'
                        elif rank == 2:
                            crown_html = f'<div class="crown crown-2">👑</div>'
                        elif rank == 3:
                            crown_html = f'<div class="crown crown-3">👑</div>'
                        else:
                            crown_html = f'<div class="crown crown-normal">🎖️</div>'
                        
                        st.markdown(f"""
                            <div class="compact-card">
                                <div class="rank-section">
                                    {crown_html}
                                    <div class="rank-number"># {rank}</div>
                                </div>
                                <div class="name-text">{player['Name']}</div>
                                <div class="score-label">คะแนนรวม</div>
                                <div class="score-value">{player['Score']:.0f}</div>
                                <div class="exp-coin-text">⚡ {player['EXP']} | 🪙 {player['Coin']}</div>
                            </div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()
