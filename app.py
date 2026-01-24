import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าเว็บ (Wide Layout) ---
st.set_page_config(page_title="Gaming Leaderboard", page_icon="👑", layout="wide")

# --- 2. Custom CSS: ปรับโฉมมงกุฎและย่อส่วนหัวให้เล็กที่สุด ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; background-color: #f8f9fa; }

    /* การ์ดผู้เล่นแบบกะทัดรัดพิเศษ */
    .compact-card {
        background: white;
        padding: 8px;
        border-radius: 12px;
        margin-bottom: 15px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        height: 155px;
        position: relative;
    }

    /* ส่วนหัวอันดับ (จิ๋วมาก) */
    .rank-header {
        height: 35px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-bottom: 3px;
    }
    .crown-icon {
        font-size: 20px;
        line-height: 1;
        margin-bottom: -4px;
    }
    .rank-num-label {
        font-size: 9px;
        font-weight: bold;
        background: #f0f0f0;
        padding: 0px 6px;
        border-radius: 8px;
        color: #666;
    }
    
    /* สีมงกุฎตามอันดับ */
    .c-1 { color: #FFD700; } /* ทอง */
    .c-2 { color: #C0C0C0; } /* เงิน */
    .c-3 { color: #CD7F32; } /* ทองแดง */
    .c-normal { color: #e0e0e0; font-size: 16px; }

    /* การจัดการข้อความภายใน */
    .player-name-text { font-size: 0.9em; font-weight: 600; color: #333; height: 22px; overflow: hidden; margin-bottom: 2px; }
    .score-title { color: #999; font-size: 0.65em; margin-bottom: -2px; }
    .score-val { font-size: 1.25em; font-weight: 800; color: #2e3131; margin-bottom: 4px; }
    .meta-data { 
        font-size: 0.7em; 
        color: #6c757d; 
        border-top: 1px solid #f8f9fa; 
        padding-top: 4px;
        display: flex;
        justify-content: space-around;
    }
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
        # 1. เชื่อมต่อข้อมูล
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m")

        if df is not None:
            # 2. เตรียมข้อมูล (A=ชื่อ, AL=คะแนนรวม, AM=EXP, AN=ระดับเหรียญ)
            # ดึงลำดับคอลัมน์ A(0), AL(37), AM(38), AN(39)
            data = df.iloc[:, [0, 37, 38, 39]].copy()
            data.columns = ['Name', 'Score', 'EXP', 'MedalLevel']
            
            data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
            df_clean = data.dropna(subset=['Score']).copy()

            # ใช้ Dense Ranking เพื่อให้อันดับไม่ข้าม (1, 1, 2, 3...)
            df_clean['Rank'] = df_clean['Score'].rank(method='dense', ascending=False).astype(int)
            df_sorted = df_clean.sort_values(by='Rank')

            # 3. แสดงผลแบบ Grid (5 ช่องต่อแถว)
            player_list = df_sorted.to_dict('records')
            for i in range(0, len(player_list), 5):
                cols = st.columns(5)
                batch = player_list[i : i+5]
                
                for idx, player in enumerate(batch):
                    with cols[idx]:
                        rank = player['Rank']
                        
                        # เลือกไอคอนตามอันดับ
                        if rank == 1:
                            rank_html = f'<div class="crown-icon c-1">👑</div>'
                        elif rank == 2:
                            rank_html = f'<div class="crown-icon c-2">👑</div>'
                        elif rank == 3:
                            rank_html = f'<div class="crown-icon c-3">👑</div>'
                        else:
                            rank_html = f'<div class="crown-icon c-normal">🎖️</div>'
                        
                        st.markdown(f"""
                            <div class="compact-card">
                                <div class="rank-header">
                                    {rank_html}
                                    <div class="rank-num-label"># {rank}</div>
                                </div>
                                <div class="player-name-text">{player['Name']}</div>
                                <div class="score-title">คะแนนรวม</div>
                                <div class="score-val">{player['Score']:.0f}</div>
                                <div class="meta-data">
                                    <span>⚡ EXP: {player['EXP']}</span>
                                    <span>🏅 {player['MedalLevel']}</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()
