import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าเว็บ (ใช้ Wide Layout เพื่อให้มีพื้นที่วาง 5 คอลัมน์) ---
st.set_page_config(page_title="Gaming Leaderboard", page_icon="🏆", layout="wide")

# --- 2. Custom CSS: ปรับให้การ์ดเล็กลงและวางในคอลัมน์ได้สวยงาม ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; background-color: #f4f7f6; }

    /* การ์ดผู้เล่นแบบกะทัดรัด */
    .compact-card {
        background: white;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-top: 5px solid #2e3131;
        height: 180px; /* ล็อกความสูงให้เท่ากันทุกช่อง */
    }

    /* วงกลมอันดับด้านบนการ์ด */
    .rank-label {
        width: 30px;
        height: 30px;
        background: #2e3131;
        color: white;
        border-radius: 50%;
        margin: 0 auto 10px;
        line-height: 30px;
        font-weight: bold;
    }
    .top-1 { background: #FFD700; color: #000; }
    .top-2 { background: #C0C0C0; color: #000; }
    .top-3 { background: #CD7F32; color: #fff; }

    .name-text { font-size: 0.95em; font-weight: 600; margin-bottom: 8px; color: #333; height: 40px; overflow: hidden; }
    .score-badge { background: #e9ecef; border-radius: 5px; padding: 2px 8px; font-size: 0.85em; color: #444; margin-bottom: 5px; }
    .exp-coin-text { font-size: 0.75em; color: #6c757d; }
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
                if st.form_submit_button("Log In"):
                    if u in st.secrets["users"] and p == st.secrets["users"][u]:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = u
                        st.rerun()
                    else: st.error("ข้อมูลไม่ถูกต้อง")
        return False
    return True

if check_password():
    st.markdown("<h1 style='text-align: center;'>🏆 อันดับผู้กล้า</h1>", unsafe_allow_html=True)
    st.write("")

    try:
        # 1. เชื่อมต่อข้อมูล
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m")

        if df is not None:
            # 2. เตรียมข้อมูล (A, AL, AM, AN)
            data = df.iloc[:, [0, 37, 38, 39]].copy()
            data.columns = ['Name', 'Score', 'EXP', 'Coin']
            
            # แปลงคะแนนเป็นตัวเลขและคำนวณอันดับแบบ Shared Rank (method='min')
            data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
            df_clean = data.dropna(subset=['Score']).copy()
            df_clean['Rank'] = df_clean['Score'].rank(method='min', ascending=False).astype(int)
            df_sorted = df_clean.sort_values(by='Rank')

            # 3. การแสดงผลแบบ Grid (5 ช่องต่อแถว)
            total_players = len(df_sorted)
            for i in range(0, total_players, 5):
                # สร้าง 5 คอลัมน์
                cols = st.columns(5)
                # ดึงข้อมูลผู้เล่นมาทีละ 5 คน
                chunk = df_sorted.iloc[i : i + 5]
                
                for idx, (original_idx, row) in enumerate(chunk.iterrows()):
                    with cols[idx]:
                        rank = row['Rank']
                        # กำหนดสไตล์ตามอันดับ
                        rank_class = f"top-{rank}" if rank <= 3 else ""
                        
                        st.markdown(f"""
                            <div class="compact-card">
                                <div class="rank-label {rank_class}">{rank}</div>
                                <div class="name-text">{row['Name']}</div>
                                <div class="score-badge">คะแนนรวม: {row['Score']:.0f}</div>
                                <div class="exp-coin-text">⚡ EXP: {row['EXP']} | 🪙 {row['Coin']}</div>
                            </div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")

    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()
