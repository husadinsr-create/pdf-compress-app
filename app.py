import streamlit as st
import os
import io
import smtplib
import pymupdf as fitz
from PIL import Image
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

st.set_page_config(page_title="PDF Compressor & Sender", page_icon="📄")
st.title("📄 ระบบบีบอัด PDF & ส่งอีเมลออนไลน์")

# --- ส่วนอัปโหลดไฟล์ ---
uploaded_file = st.file_uploader("เลือกไฟล์ PDF ที่ต้องการบีบอัด", type=["pdf"])

# --- ตั้งค่าระดับการบีบอัด ---
st.sidebar.header("⚙️ ตั้งค่าความคมชัด/ขนาดไฟล์")
quality = st.sidebar.slider("คุณภาพรูปภาพใน PDF (Quality)", 10, 90, 50, help="ค่ายิ่งน้อย ไฟล์ยิ่งเล็กลง")
max_dpi = st.sidebar.slider("ขนาดความกว้างสูงสุด (Pixels)", 600, 2000, 1200)

# --- ข้อมูลอีเมล ---
st.subheader("📧 ข้อมูลการส่งอีเมล")
col1, col2 = st.columns(2)
with col1:
    sender_email = st.text_input("อีเมลผู้ส่ง (Gmail)", placeholder="email@gmail.com")
    sender_password = st.text_input("App Password 16 หลัก", type="password")
with col2:
    receiver_email = st.text_input("อีเมลผู้รับ", placeholder="destination@email.com")
    subject = st.text_input("หัวข้ออีเมล", value="ส่งไฟล์ PDF ที่บีบอัดแล้ว")

body = st.text_area("เนื้อหาในอีเมล", value="สวัสดีครับ แนบไฟล์ PDF ที่ลดขนาดแล้วมาให้ครับ")

# --- ฟังก์ชันบีบอัด ---
def compress_pdf_stream(pdf_bytes, quality, max_size):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            base_img = doc.extract_image(xref)
            image = Image.open(io.BytesIO(base_img["image"]))
            
            if max(image.size) > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
                
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True)
            page.replace_image(xref, stream=buffer.getvalue())

    output_stream = io.BytesIO()
    doc.save(output_stream, garbage=4, deflate=True, clean=True)
    doc.close()
    return output_stream.getvalue()

# --- ปุ่มประมวลผล ---
if st.button("🚀 บีบอัดและส่งอีเมลทันที", type="primary"):
    if not uploaded_file:
        st.error("❌ กรุณาอัปโหลดไฟล์ PDF ก่อนครับ")
    elif not (sender_email and sender_password and receiver_email):
        st.error("❌ กรุณากรอกข้อมูลอีเมลและ App Password ให้ครบถ้วน")
    else:
        with st.spinner("⏳ กำลังบีบอัดไฟล์ PDF..."):
            input_bytes = uploaded_file.read()
            orig_size = len(input_bytes) / (1024 * 1024)
            
            compressed_bytes = compress_pdf_stream(input_bytes, quality, max_dpi)
            comp_size = len(compressed_bytes) / (1024 * 1024)
            
            st.success(f"✅ บีบอัดสำเร็จ! (ขนาดเดิม {orig_size:.2f} MB ➡️ เหลือเพียง {comp_size:.2f} MB)")
            
        with st.spinner("⏳ กำลังส่งอีเมล..."):
            try:
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = receiver_email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain', 'utf-8'))

                part = MIMEBase("application", "pdf")
                part.set_payload(compressed_bytes)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename=compressed_{uploaded_file.name}")
                msg.attach(part)

                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
                server.quit()
                
                st.balloons()
                st.success("🎉 ส่งอีเมลเรียบร้อยแล้ว!")
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาดในการส่งอีเมล: {e}")