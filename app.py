import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Game Leaderboard", page_icon="🏆", layout="centered")

# --- 2. Custom CSS: เน้นความกะทัดรัด (Minimal & Compact) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; background-color: #f8f9fa; }

    /* การ์ดผู้เล่นแบบเล็ก (Compact Card) */
    .player-card {
        background: white;
        padding: 10px 20px;
        border-radius: 12px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        border: 1px solid #eee;
    }

    /* วงกลมอันดับแบบเล็กลง */
    .rank-badge {
        width: 35px;
        height: 35px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 1em;
        font-weight: bold;
        margin-right: 15px;
        flex-shrink: 0;
        background: #f1f3f5;
        color: #495057;
    }
    .rank-1 { background: #FFD700; color: #000; }
    .rank-2 { background: #C0C0C0; color: #000; }
    .rank-3 { background: #CD7F32; color: #fff; }

    /* ปรับขนาดตัวอักษรให้เล็กลง */
    .info-container { flex-grow: 1; display: flex; align-items: center; justify-content: space-between; }
    .player-name { font-size: 1em; font-weight: 600; color: #333; min-width: 150px; }
    .stats-group { display: flex; gap: 15px; }
    
    .stat-item { 
        font-size: 0.85em; 
        color: #666; 
        background: #f8f9fa; 
        padding: 2px 10px; 
        border-radius: 20px;
        border: 1px solid #f0f0f0;
    }
    .stat-label { font-weight: 600; color: #444; margin-right: 3px; }
    
    .coin-mini { font-size: 1.2em; margin-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ระบบ Login ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        _, col, _ = st.columns([1, 2, 1])
        with col:
            with st.form("login"):
                st.markdown("<h3 style='text-align: center;'>🎮 เข้าสู่ระบบ</h3>", unsafe_allow_html=True)
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
    st.markdown("<h2 style='text-align: center;'>🏆 กระดานผู้นำทุกคน</h2>", unsafe_allow_html=True)
    
    try:
        # 1. เชื่อมต่อข้อมูล
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m")

        if df is not None:
            # 2. จัดเตรียมข้อมูล (A, AL, AM, AN)
            data = df.iloc[:, [0, 37, 38, 39]].copy()
            data.columns = ['Name', 'Score', 'EXP', 'Coin']
            
            # แปลงคะแนนเป็นตัวเลข
            data['Score'] = pd.to_numeric(data['Score'], errors='coerce')
            df_clean = data.dropna(subset=['Score']).copy()

            # 3. คำนวณอันดับแบบอันดับเท่ากันได้ (Dense Rank)
            # method='min' จะทำให้ถ้าที่ 1 มีสองคน คนถัดไปจะเป็นที่ 3
            # method='dense' จะทำให้ถ้าที่ 1 มีสองคน คนถัดไปจะเป็นที่ 2 (เลือกตามความเหมาะสม)
            df_clean['Rank'] = df_clean['Score'].rank(method='min', ascending=False).astype(int)
            
            # เรียงลำดับตามอันดับ
            df_sorted = df_clean.sort_values(by='Rank')

            # 4. แสดงผลทุกคน (ไม่มีการแบ่งหน้า)
            for _, row in df_sorted.iterrows():
                rank = row['Rank']
                # กำหนดสีอันดับ 1-3
                rank_style = f"rank-{rank}" if rank <= 3 else ""
                
                st.markdown(f"""
                    <div class="player-card">
                        <div class="rank-badge {rank_style}">{rank}</div>
                        <div class="info-container">
                            <div class="player-name">{row['Name']}</div>
                            <div class="stats-group">
                                <div class="stat-item"><span class="stat-label">คะแนนรวม:</span> {row['Score']:.0f}</div>
                                <div class="stat-item"><span class="stat-label">EXP:</span> {row['EXP']}</div>
                                <div class="stat-item"><span class="stat-label">🪙:</span> {row['Coin']}</div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error("ไม่สามารถโหลดข้อมูลได้")
        
    if st.sidebar.button("Log out"):
        st.session_state["authenticated"] = False
        st.rerun()
