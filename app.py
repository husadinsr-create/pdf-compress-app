from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import io
import os
import pymupdf as fitz
from PIL import Image
import streamlit as st

st.set_page_config(page_title="PDF Tool Hub", page_icon="📄", layout="centered")

# --- Custom CSS แต่งพื้นหลังแนว 3D / Glassmorphism และปุ่มเมนูลอยเด่น ---
st.markdown(
    """
<style>
    /* ตั้งค่าพื้นหลังหลักของแอปพลิเคชันให้เป็นโทนไล่ระดับสีแบบมีมิติ (3D Gradient) */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #311042 100%);
        background-attachment: fixed;
    }

    /* ตกแต่งกล่องเลือกเมนู (Radio) ให้เป็นปุ่มการ์ด 3D มีมิติและเงาลอย */
    .stRadio > div {
        display: flex;
        justify-content: center;
        gap: 20px;
        margin-bottom: 25px;
    }
    .stRadio label {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-top: 1px solid rgba(255, 255, 255, 0.2);
        padding: 16px 32px;
        border-radius: 16px;
        color: #f8fafc !important;
        font-weight: 600;
        font-size: 16px;
        cursor: pointer;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-align: center;
    }
    .stRadio label:hover {
        transform: translateY(-5px) scale(1.02);
        border-color: #a855f7;
        box-shadow: 0 20px 30px -10px rgba(168, 85, 247, 0.4), 0 10px 15px -5px rgba(0, 0, 0, 0.5);
        background: rgba(255, 255, 255, 0.1);
    }
    /* ซ่อนจุดวงกลม default ของ radio */
    .stRadio input[type="radio"] {
        display: none;
    }

    /* ปรับแต่งกล่องคอนเทนต์และ Sidebar ให้มีความโปร่งแสงสวยงามแบบกระจก (Glassmorphism) */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background: rgba(15, 23, 42, 0.6);
        padding: 20px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "<h1 style='text-align: center; color: #ffffff; text-shadow: 0 2px 10px rgba(0,0,0,0.5);'>📄 ระบบจัดการและส่งอีเมล PDF ออนไลน์</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #cbd5e1; margin-bottom: 25px;'>เลือกเมนูเครื่องมือที่คุณต้องการใช้งานด้านล่างนี้ได้เลยครับ</p>",
    unsafe_allow_html=True,
)

# --- เลือกเมนูหลักด้วย Radio ในรูปแบบปุ่มการ์ด 3D ---
selected_menu = st.radio(
    "เลือกเมนูการใช้งาน",
    ["🗜️ บีบอัดไฟล์ PDF", "🔄 แก้ PDF กลับหัว"],
    horizontal=True,
    label_visibility="collapsed",
)

st.markdown("---")


# ==================== ฟังก์ชันบีบอัด PDF ====================
def compress_pdf_stream(pdf_bytes, quality=50, max_size=1200):
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


# ==================== ฟังก์ชันแก้ PDF กลับหัว ====================
def rotate_pdf_stream(pdf_bytes, angle=180):
  doc = fitz.open(stream=pdf_bytes, filetype="pdf")
  for page in doc:
    current_rotation = page.rotation
    page.set_rotation((current_rotation + angle) % 360)

  output_stream = io.BytesIO()
  doc.save(output_stream, garbage=4, deflate=True, clean=True)
  doc.close()
  return output_stream.getvalue()


# ==================== ฟังก์ชันส่งอีเมล ====================
def send_email_with_pdf(
    pdf_bytes, filename, sender_email, sender_password, receiver_email, subject, body
):
  msg = MIMEMultipart()
  msg["From"] = sender_email
  msg["To"] = receiver_email
  msg["Subject"] = subject
  msg.attach(MIMEText(body, "plain", "utf-8"))

  part = MIMEBase("application", "pdf")
  part.set_payload(pdf_bytes)
  encoders.encode_base64(part)
  part.add_header("Content-Disposition", f"attachment; filename={filename}")
  msg.attach(part)

  server = smtplib.SMTP("smtp.gmail.com", 587)
  server.starttls()
  server.login(sender_email, sender_password)
  server.send_message(msg)
  server.quit()


# ==================== ส่วนแสดงผลตามเมนูที่เลือก ====================

if selected_menu == "🗜️ บีบอัดไฟล์ PDF":
  st.markdown("### 🗜️ บีบอัดไฟล์ PDF (ลดขนาดไฟล์)")
  st.write("อัปโหลดไฟล์ PDF ปรับความคมชัด และสามารถเลือกส่งอีเมลได้ทันที")

  col1, col2 = st.columns(2)
  with col1:
    quality = st.slider(
        "คุณภาพรูปภาพ (Quality)", 10, 90, 50, key="comp_quality"
    )
  with col2:
    max_dpi = st.slider(
        "ขนาดความกว้างสูงสุด (Pixels)", 600, 2000, 1200, key="comp_dpi"
    )

  uploaded_file_comp = st.file_uploader(
      "เลือกไฟล์ PDF สำหรับบีบอัด", type=["pdf"], key="file_comp"
  )

  with st.expander("📧 ตั้งค่าการส่งอีเมล (ไม่บังคับ)"):
    send_mail_comp = st.checkbox("ต้องการส่งอีเมลไฟล์นี้ด้วย", key="chk_mail_comp")
    sender_email_c = st.text_input("อีเมลผู้ส่ง (Gmail)", key="sender_c")
    sender_pass_c = st.text_input(
        "App Password (16 หลัก)", type="password", key="pass_c"
    )
    receiver_email_c = st.text_input("อีเมลผู้รับ", key="receiver_c")

  if uploaded_file_comp is not None:
    if st.button("🚀 เริ่มบีบอัดไฟล์ PDF", type="primary", key="btn_comp"):
      with st.spinner("⏳ กำลังบีบอัดไฟล์..."):
        input_bytes = uploaded_file_comp.read()
        orig_size = len(input_bytes) / (1024 * 1024)

        compressed_bytes = compress_pdf_stream(
            input_bytes, quality=quality, max_size=max_dpi
        )
        comp_size = len(compressed_bytes) / (1024 * 1024)

        st.success(
            f"✅ บีบอัดสำเร็จ! ({orig_size:.2f} MB ➡️ เหลือเพียง"
            f" {comp_size:.2f} MB)"
        )

        output_filename = f"compressed_{uploaded_file_comp.name}"

        if send_mail_comp:
          try:
            with st.spinner("⏳ กำลังส่งอีเมล..."):
              send_email_with_pdf(
                  compressed_bytes,
                  output_filename,
                  sender_email_c,
                  sender_pass_c,
                  receiver_email_c,
                  "แนบไฟล์ PDF ผ่านการบีบอัด",
                  "สวัสดีครับ แนบไฟล์ PDF ที่ผ่านการบีบอัดเรียบร้อยแล้วครับ",
              )
            st.success("🎉 ส่งอีเมลสำเร็จแล้ว!")
          except Exception as e:
            st.error(f"❌ ส่งอีเมลไม่สำเร็จ: {e}")

        st.download_button(
            label="📥 ดาวน์โหลดไฟล์ PDF ที่บีบอัดแล้ว",
            data=compressed_bytes,
            file_name=output_filename,
            mime="application/pdf",
            key="dl_comp",
        )

elif selected_menu == "🔄 แก้ PDF กลับหัว":
  st.markdown("### 🔄 แก้ PDF กลับหัว (หมุนหน้าเอกสาร)")
  st.write("อัปโหลดไฟล์ PDF ที่หัวกลับหรือเอียง เลือกองศา และส่งอีเมลได้ทันที")

  rotation_angle = st.selectbox(
      "เลือกองศาการหมุน",
      [
          (180, "กลับหัว 180 องศา (Upside-Down)"),
          (90, "หมุนขวา 90 องศา"),
          (270, "หมุนซ้าย 90 องศา (270 องศา)"),
      ],
      format_func=lambda x: x[1],
      key="rot_angle",
  )[0]

  uploaded_file_rot = st.file_uploader(
      "เลือกไฟล์ PDF ที่ต้องการหมุน", type=["pdf"], key="file_rot"
  )

  with st.expander("📧 ตั้งค่าการส่งอีเมล (ไม่บังคับ)", key="exp_mail_rot"):
    send_mail_rot = st.checkbox("ต้องการส่งอีเมลไฟล์นี้ด้วย", key="chk_mail_rot")
    sender_email_r = st.text_input("อีเมลผู้ส่ง (Gmail)", key="sender_r")
    sender_pass_r = st.text_input(
        "App Password (16 หลัก)", type="password", key="pass_r"
    )
    receiver_email_r = st.text_input("อีเมลผู้รับ", key="receiver_r")

  if uploaded_file_rot is not None:
    if st.button("🔄 เริ่มหมุน/แก้ PDF กลับหัว", type="primary", key="btn_rot"):
      with st.spinner("⏳ กำลังหมุนหน้า PDF..."):
        input_bytes = uploaded_file_rot.read()
        processed_bytes = rotate_pdf_stream(
            input_bytes, angle=rotation_angle
        )

        st.success("✅ หมุนหน้า PDF สำเร็จเรียบร้อยแล้ว!")

        output_filename_rot = f"rotated_{uploaded_file_rot.name}"

        if send_mail_rot:
          try:
            with st.spinner("⏳ กำลังส่งอีเมล..."):
              send_email_with_pdf(
                  processed_bytes,
                  output_filename_rot,
                  sender_email_r,
                  sender_pass_r,
                  receiver_email_r,
                  "แนบไฟล์ PDF แก้กลับหัวแล้ว",
                  "สวัสดีครับ แนบไฟล์ PDF ที่ผ่านการหมุนแก้กลับหัวเรียบร้อยแล้วครับ",
              )
            st.success("🎉 ส่งอีเมลสำเร็จแล้ว!")
          except Exception as e:
            st.error(f"❌ ส่งอีเมลไม่สำเร็จ: {e}")

        st.download_button(
            label="📥 ดาวน์โหลดไฟล์ PDF ที่แก้ไขแล้ว",
            data=processed_bytes,
            file_name=output_filename_rot,
            mime="application/pdf",
            key="dl_rot",
        )