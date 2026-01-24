import streamlit as st
from streamlit_gsheets import GSheetsConnection

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Dashboard ข้อมูลจาก Google Sheets", layout="wide")
st.title("📊 ระบบดึงข้อมูลจาก Google Sheets")

# 2. เชื่อมต่อกับ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. อ่านข้อมูล (ใส่ URL ของ Sheet ที่เราก๊อปปี้ไว้ลงไป)
# ในขั้นตอน Deploy จริง เราจะเอา URL ไปใส่ใน Secrets แทนเพื่อความปลอดภัย
df = conn.read(
    spreadsheet="ใส่_URL_ของ_GOOGLE_SHEETS_ที่นี่",
    ttl="10m" # ให้รีเฟรชข้อมูลทุก 10 นาที
)

# 4. แสดงผลข้อมูล
st.subheader("ตารางข้อมูลทั้งหมด")
st.dataframe(df, use_container_width=True)

# 5. เพิ่มฟีเจอร์ค้นหาง่ายๆ
search = st.text_input("ค้นหาข้อมูลในตาราง")
if search:
    filtered_df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
    st.write(f"พบข้อมูล {len(filtered_df)} รายการ")
    st.table(filtered_df)
