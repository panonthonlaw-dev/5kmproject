import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าเว็บ ---
st.set_page_config(
    page_title="Student Score Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- 2. Custom CSS สำหรับความ Minimal และฟอนต์ภาษาไทย ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Sarabun', sans-serif;
    }
    
    /* ปรับแต่ง Container ของ Login */
    .stForm {
        border-radius: 15px;
        padding: 30px;
        border: 1px solid #eee;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    /* ปรับแต่งปุ่มให้ดูทันสมัย */
    div.stButton > button:first-child {
        background-color: #000000;
        color: white;
        border-radius: 8px;
        border: none;
        width: 100%;
        height: 45px;
        font-weight: 600;
    }
    
    /* ซ่อน Header ของ Streamlit เพื่อความคลีน */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. ระบบตรวจสอบสิทธิ์ (Login System) ---
def check_password():
    """คืนค่า True หาก Login สำเร็จ"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        _, col_mid, _ = st.columns([1, 1.2, 1])
        with col_mid:
            st.write("\n\n") 
            with st.form("Login_Form"):
                st.markdown("<h2 style='text-align: center;'>🔐 เข้าสู่ระบบ</h2>", unsafe_allow_html=True)
                user = st.text_input("Username")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Log In"):
                    # ตรวจสอบกับค่าใน Secrets
                    if user in st.secrets["users"] and pw == st.secrets["users"][user]:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = user
                        st.rerun()
                    else:
                        st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        return False
    return True

# --- 4. การทำงานหลักของแอป (จะรันเมื่อ Login ผ่านแล้ว) ---
if check_password():
    # Sidebar
    with st.sidebar:
        st.write(f"👤 ผู้ใช้งาน: **{st.session_state['username']}**")
        if st.button("ออกจากระบบ"):
            st.session_state["authenticated"] = False
            st.rerun()
        st.divider()
        st.caption("ระบบดึงข้อมูลจาก Google Sheets อัตโนมัติ")

    # ส่วนหัวข้อ
    st.title("📊 รายงานสรุปผลคะแนนนักเรียน")
    st.markdown("แสดงข้อมูลเฉพาะคอลัมน์ **A, AL, AM, AN** และเรียงลำดับคะแนนจากมากไปน้อย")
    st.write("")

    try:
        # เชื่อมต่อ Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="5m")

        if df is not None:
            # เลือกเฉพาะคอลัมน์ A(0), AL(37), AM(38), AN(39)
            # หมายเหตุ: .iloc ใช้ลำดับเลขคอลัมน์ เริ่มนับจาก 0
            df_display = df.iloc[:, [0, 37, 38, 39]].copy()
            
            # ระบุชื่อคอลัมน์ที่เป็นคะแนน (AL คือตัวที่ 2 ในลิสต์ใหม่ของเรา)
            score_col_name = df_display.columns[1]
            
            # จัดการข้อมูล: แปลงเป็นตัวเลขและเรียงลำดับ
            df_display[score_col_name] = pd.to_numeric(df_display[score_col_name], errors='coerce')
            df_sorted = df_display.sort_values(by=score_col_name, ascending=False).dropna(subset=[score_col_name])

            # ส่วนสรุปผล (Metrics)
            m1, m2, m3 = st.columns(3)
            with m1:
                st.container(border=True).metric("คะแนนสูงสุด", f"{df_sorted[score_col_name].max():.2f}")
            with m2:
                st.container(border=True).metric("คะแนนเฉลี่ย", f"{df_sorted[score_col_name].mean():.2f}")
            with m3:
                st.container(border=True).metric("จำนวนนักเรียน", f"{len(df_sorted)} คน")

            st.write("")

            # การแสดงผลตารางแบบสะอาดตา
            st.dataframe(
                df_sorted,
                use_container_width=True,
                hide_index=True, # ซ่อนเลขแถวด้านหน้า
                column_config={
                    df_sorted.columns[0]: st.column_config.TextColumn("ชื่อ-นามสกุล (A)"),
                    score_col_name: st.column_config.NumberColumn("คะแนนสอบ (AL)", format="%.2f"),
                    df_sorted.columns[2]: "ข้อมูล AM",
                    df_sorted.columns[3]: "ข้อมูล AN"
                }
            )

            # ปุ่มดาวน์โหลด
            st.write("")
            csv = df_sorted.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 ดาวน์โหลดข้อมูล (CSV)", csv, "score_report.csv", "text/csv")

    except Exception as e:
        st.warning("⚠️ ไม่พบข้อมูลหรือตำแหน่งคอลัมน์ไม่ถูกต้อง")
        with st.expander("ดูรายละเอียดข้อผิดพลาด"):
            st.write(e)
