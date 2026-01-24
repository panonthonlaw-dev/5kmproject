import streamlit as st
from streamlit_gsheets import GSheetsConnection

# --- 1. ฟังก์ชันระบบ Login ---
def check_password():
    """คืนค่า True ถ้ารหัสผ่านถูกต้อง"""
    def password_entered():
        # ตรวจสอบรหัสผ่านจาก Secrets ที่เราตั้งไว้
        if st.session_state["password"] == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # ลบรหัสออกจาก session เพื่อความปลอดภัย
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # หน้าจอ Login
        st.title("🔐 กรุณาเข้าสู่ระบบ")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state:
            st.error("😕 รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่")
        return False
    return True

# --- 2. ส่วนแสดงเนื้อหา (จะทำงานเมื่อ Login ผ่านแล้ว) ---
if check_password():
    st.set_page_config(page_title="ระบบจัดการข้อมูลภายใน", layout="wide")
    st.title("📊 ข้อมูลจากระบบหลังบ้าน (Google Sheets)")
    
    # ปุ่ม Logout
    if st.sidebar.button("Log out"):
        del st.session_state["password_correct"]
        st.rerun()

    # เชื่อมต่อ Google Sheets (เหมือนเดิม)
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m") # ตั้งให้ดึงใหม่ทุก 1 นาที

        st.success("เชื่อมต่อข้อมูลสำเร็จ!")
        st.dataframe(df, use_container_width=True)
        
        # เพิ่มตัวกรองข้อมูล
        search = st.text_input("🔍 ค้นหาข้อมูล...")
        if search:
            filtered_df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            st.write(f"ผลการค้นหา: {len(filtered_df)} รายการ")
            st.table(filtered_df)
            
    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูลได้: {e}")
