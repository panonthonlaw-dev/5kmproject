import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าเว็บ (Wide Layout) ---
st.set_page_config(page_title="Game Leaderboard", page_icon="🏆", layout="wide")

# --- 2. Custom CSS: ตกแต่งให้กะทัดรัดและสวยงาม ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; background-color: #f8f9fa; }

    /* การ์ดผู้เล่น */
    .compact-card {
        background: white;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        border-top: 5px solid #2e3131;
        transition: transform 0.2s;
    }
    .compact-card:hover { transform: translateY(-5px); }

    /* วงกลมอันดับ */
    .rank-label {
        width: 35px;
        height: 35px;
        background: #2e3131;
        color: white;
        border-radius: 50%;
        margin: 0 auto 10px;
        line-height: 35px;
        font-weight: bold;
        font-size: 1.1em;
    }
    /* สีพิเศษอันดับ 1, 2, 3 */
    .top-1 { background: #FFD700; color: #000; box-shadow: 0 0 10px #FFD700; }
    .top-2 { background: #C0C0C0; color: #000; }
    .top-3 { background: #CD7F32; color: #fff; }

    .name-text { font-size: 1em; font-weight: 600; margin-bottom: 8px; color: #333; height: 30px; overflow: hidden; }
    .score-label { color: #666; font-size: 0.8em; margin-bottom: 2px; }
    .score-value { font-size: 1.3em; font-weight: bold; color: #2e3131; margin-bottom: 10px; }
    .exp-coin-text { font-size: 0.8em; color: #6c757d; background: #f1f3f5; padding: 5px; border-radius: 8px; }
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
                st.markdown("<h3 style='text-align: center;'>🎮 Player Login</h3>", unsafe_allow_html=True)
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("เข้าสู่ระบบ"):
                    if u in st.secrets["users"] and p == st.secrets["users"][u]:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = u
                        st.rerun()
                    else: st.error("ข้อมูลไม่ถูกต้อง")
        return False
    return True

if check_password():
    st.markdown("<h1 style='text-align: center;'>🏆 กระดานผู้นำ (Leaderboard)</h1>", unsafe_allow_html=True)
    st.write("")

    try:
        # 1. ดึงข้อมูล
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m")

        if df is not None:
            # 2. เตรียมข้อมูล (A, AL, AM, AN)
            data = df.iloc[:, [0, 37, 38, 39]].copy()
            data.columns = ['Name', 'Score', 'EXP', 'Coin']
            
            # แปลงคะแนนเป็นตัวเลข
            data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
            df_clean = data.dropna(subset=['Score']).copy()

            # --- จุดสำคัญ: เปลี่ยนวิธีนับอันดับเป็น 'dense' ---
            # 'dense' จะทำให้อันดับเป็น 1, 1, 2, 2, 3 ต่อกันไปเรื่อยๆ ไม่มีการข้ามเลข
            df_clean['Rank'] = df_clean['Score'].rank(method='dense', ascending=False).astype(int)
            
            # เรียงลำดับตามอันดับจากน้อยไปมาก (ที่ 1 อยู่หน้าสุด)
            df_sorted = df_clean.sort_values(by='Rank')

            # 3. แสดงผลแบบ Grid (5 ช่องต่อแถว)
            players = df_sorted.to_dict('records')
            for i in range(0, len(players), 5):
                cols = st.columns(5)
                batch = players[i:i+5]
                
                for idx, player in enumerate(batch):
                    with cols[idx]:
                        rank = player['Rank']
                        rank_class = f"top-{rank}" if rank <= 3 else ""
                        
                        st.markdown(f"""
                            <div class="compact-card">
                                <div class="rank-label {rank_class}">{rank}</div>
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
