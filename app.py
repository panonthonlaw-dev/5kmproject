import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Top 5 Leaderboard", layout="centered")

# --- Custom CSS สำหรับตกแต่งการ์ด (Minimal & Modern) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

    /* ตกแต่งช่อง (Card) ของแต่ละคน */
    .user-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        border: 1px solid #f0f0f0;
    }
    /* วงกลมเลขอันดับ */
    .rank-circle {
        background-color: #2e3131;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        font-weight: bold;
        margin-right: 20px;
        font-size: 1.2em;
    }
    /* สีพิเศษสำหรับอันดับ 1-3 */
    .rank-1 { background-color: #FFD700; color: #000; } /* ทอง */
    .rank-2 { background-color: #C0C0C0; color: #000; } /* เงิน */
    .rank-3 { background-color: #CD7F32; color: #fff; } /* ทองแดง */

    .user-info { flex-grow: 1; }
    .user-name { font-size: 1.1em; font-weight: 600; color: #2e3131; }
    .user-stats { color: #6c757d; font-size: 0.9em; margin-top: 5px; }
    .stat-box { display: inline-block; margin-right: 15px; }
    
    .coin-icon { font-size: 1.2em; filter: grayscale(100%); opacity: 0.5; } /* เตรียมไว้ใส่รูปภายหลัง */
    </style>
    """, unsafe_allow_html=True)

# --- ระบบ Login (Username/Password) ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        _, col_mid, _ = st.columns([1, 2, 1])
        with col_mid:
            with st.form("Login"):
                st.markdown("<h3 style='text-align: center;'>🔐 ระบบเช็คคะแนน</h3>", unsafe_allow_html=True)
                user = st.text_input("Username")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("เข้าสู่ระบบ"):
                    if user in st.secrets["users"] and pw == st.secrets["users"][user]:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = user
                        st.rerun()
                    else:
                        st.error("รหัสผ่านไม่ถูกต้อง")
        return False
    return True

if check_password():
    st.title("🏆 Leaderboard")
    st.write(f"ผู้ใช้งาน: {st.session_state['username']}")
    st.divider()

    try:
        # 1. ดึงข้อมูลจาก Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m")

        if df is not None:
            # 2. จัดการข้อมูล (A=ชื่อ, AL=คะแนนรวม, AM=EXP, AN=เหรียญ)
            df_data = df.iloc[:, [0, 37, 38, 39]].copy()
            df_data.columns = ['Name', 'Score', 'EXP', 'Coin']
            
            # แปลงเป็นตัวเลขและเรียงลำดับ
            df_data['Score'] = pd.to_numeric(df_data['Score'], errors='coerce')
            df_sorted = df_data.sort_values(by='Score', ascending=False).dropna(subset=['Score']).reset_index(drop=True)

            # 3. แสดงผลหน้าละ 5 ช่อง (Pagination)
            items_per_page = 5
            total_pages = (len(df_sorted) // items_per_page) + (1 if len(df_sorted) % items_per_page > 0 else 0)
            
            page = st.sidebar.number_input("หน้า", min_value=1, max_value=total_pages, step=1)
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            
            # วนลูปสร้าง 5 ช่อง
            for i, row in df_sorted.iloc[start_idx:end_idx].iterrows():
                rank = i + 1
                # กำหนดคลาสสีตามอันดับ
                rank_class = f"rank-{rank}" if rank <= 3 else ""
                
                # สร้างการ์ดด้วย HTML
                st.markdown(f"""
                    <div class="user-card">
                        <div class="rank-circle {rank_class}">{rank}</div>
                        <div class="user-info">
                            <div class="user-name">{row['Name']}</div>
                            <div class="user-stats">
                                <span class="stat-box">📊 <b>คะแนนรวม:</b> {row['Score']:.2f}</span>
                                <span class="stat-box">⚡ <b>EXP:</b> {row['EXP']}</span>
                                <span class="stat-box">🪙 <b>เหรียญ:</b> {row['Coin']}</span>
                            </div>
                        </div>
                        <div class="coin-icon">💰</div>
                    </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error("ไม่สามารถเชื่อมต่อข้อมูลได้ กรุณาตรวจสอบตำแหน่งคอลัมน์")

    if st.sidebar.button("ออกจากระบบ"):
        st.session_state["authenticated"] = False
        st.rerun()
