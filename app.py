import streamlit as st
from streamlit_gsheets import GSheetsConnection

def check_password():
    """ฟังก์ชันตรวจสอบ Username และ Password"""
    def login_form():
        with st.form("login"):
            st.subheader("🔐 เข้าสู่ระบบเพื่อดูข้อมูล")
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                # ตรวจสอบกับค่าที่เก็บไว้ใน Secrets
                if user in st.secrets["users"] and pw == st.secrets["users"][user]:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = user
                    st.rerun()
                else:
                    st.error("❌ Username หรือ Password ไม่ถูกต้อง")

    if not st.session_state.get("authenticated", False):
        login_form()
        return False
    return True

# --- เริ่มการทำงานของแอป ---
if check_password():
    # แสดงชื่อผู้ใช้ที่มุมบน
    st.sidebar.write(f"สวัสดีคุณ: **{st.session_state['username']}**")
    if st.sidebar.button("Log out"):
        st.session_state["authenticated"] = False
        st.rerun()

    st.title("📊 ระบบจัดการข้อมูล (Google Sheets)")

    # ส่วนเชื่อมต่อ Google Sheets
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
