import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- การตั้งค่าหน้าเว็บแบบกว้าง ---
st.set_page_config(page_title="Student Score Portal", layout="wide")

# --- Custom CSS เพื่อความ Minimal ---
st.markdown("""
    <style>
    /* เปลี่ยน Font และปรับปรุงหน้าตาโดยรวม */
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Sarabun', sans-serif;
    }
    .main {
        background-color: #f8f9fa;
    }
    /* ปรับแต่งปุ่ม Login */
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #2e3131;
        color: white;
        border: none;
    }
    /* ปรับแต่งตารางให้ดูสะอาด */
    .stDataFrame {
        border: none;
    }
    /* ปรับขนาดหัวข้อ */
    h1 {
        color: #2e3131;
        font-weight: 600;
    }
    </style>
    """, unsafe_index=True)

# --- ระบบ Login ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        # จัดวางฟอร์มให้อยู่กึ่งกลางหน้าจอ
        _, col_mid, _ = st.columns([1, 1.5, 1])
        with col_mid:
            st.write("") # เว้นช่องว่างข้างบน
            st.write("")
            with st.container(border=True):
                st.markdown("<h2 style='text-align: center;'>🔒 เข้าสู่ระบบ</h2>", unsafe_allow_html=True)
                user = st.text_input("Username", placeholder="ระบุชื่อผู้ใช้งาน")
                pw = st.text_input("Password", type="password", placeholder="ระบุรหัสผ่าน")
                if st.button("Log In"):
                    if user in st.secrets["users"] and pw == st.secrets["users"][user]:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = user
                        st.rerun()
                    else:
                        st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        return False
    return True

# --- เริ่มการทำงานหลัง Login ผ่าน ---
if check_password():
    # Sidebar แบบ Minimal
    with st.sidebar:
        st.markdown(f"👤 ผู้ใช้งาน: **{st.session_state['username']}**")
        if st.button("ออกจากระบบ"):
            st.session_state["authenticated"] = False
            st.rerun()
        st.divider()
        st.info("ระบบดึงข้อมูลอัตโนมัติจาก Google Sheets ทุกๆ 5 นาที")

    # ส่วนเนื้อหาหลัก
    st.title("📋 รายงานสรุปผลคะแนน")
    st.markdown("<p style='color: #6c757d;'>ข้อมูลเรียงลำดับตามคะแนนจากมากไปน้อย (คอลัมน์ AL)</p>", unsafe_allow_html=True)
    st.write("")

    try:
        # เชื่อมต่อข้อมูล
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="5m")

        if df is not None:
            # เลือกคอลัมน์ A(0), AL(37), AM(38), AN(39)
            df_selected = df.iloc[:, [0, 37, 38, 39]].copy()
            
            # แปลงคะแนนใน AL (Index 1 ของตารางใหม่) เป็นตัวเลข
            score_col = df_selected.columns[1]
            df_selected[score_col] = pd.to_numeric(df_selected[score_col], errors='coerce')
            
            # เรียงลำดับและจัดการข้อมูล
            df_sorted = df_selected.sort_values(by=score_col, ascending=False).dropna(subset=[score_col])

            # แสดงสถิติในรูปแบบ Cards สะอาดๆ
            m1, m2, m3 = st.columns(3)
            with m1:
                st.container(border=True).metric("คะแนนสูงสุด", f"{df_sorted[score_col].max():.2f}")
            with m2:
                st.container(border=True).metric("คะแนนเฉลี่ย", f"{df_sorted[score_col].mean():.2f}")
            with m3:
                st.container(border=True).metric("จำนวนนักเรียน", f"{len(df_sorted)} คน")

            st.write("")

            # แสดงตารางแบบ Minimal
            # ใช้พารามิเตอร์ hide_index=True เพื่อความสะอาด
            st.dataframe(
                df_sorted,
                use_container_width=True,
                hide_index=True,
                column_config={
                    score_col: st.column_config.NumberColumn("คะแนนหลัก (AL)", format="%.2f"),
                    df_sorted.columns[2]: "หมายเหตุ (AM)",
                    df_sorted.columns[3]: "ข้อมูลเพิ่มเติม (AN)"
                }
            )

            # ปุ่มดาวน์โหลดแบบเงียบๆ ด้านล่าง
            st.write("")
            csv = df_sorted.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📄 Export to CSV",
                data=csv,
                file_name='student_scores.csv',
                mime='text/csv',
            )

    except Exception as e:
        st.warning("⚠️ กำลังรอการเชื่อมต่อข้อมูล หรือตำแหน่งคอลัมน์ไม่ถูกต้อง")
        if st.checkbox("ดูรายละเอียดข้อผิดพลาด"):
            st.exception(e)
