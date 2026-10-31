import streamlit as st
import io
import pymupdf as fitz
from PIL import Image

st.set_page_config(page_title="PDF Compressor", page_icon="📄")
st.title("📄 ระบบบีบอัด PDF ออนไลน์")
st.write("อัปโหลดไฟล์ PDF ปรับความคมชัด แล้วกดดาวน์โหลดไฟล์ที่บีบอัดแล้วได้ทันที")

# --- ส่วนอัปโหลดไฟล์ ---
uploaded_file = st.file_uploader("เลือกไฟล์ PDF ที่ต้องการบีบอัด", type=["pdf"])

# --- ตั้งค่าระดับการบีบอัด ---
st.sidebar.header("⚙️ ตั้งค่าความคมชัด/ขนาดไฟล์")
quality = st.sidebar.slider("คุณภาพรูปภาพใน PDF (Quality)", 10, 90, 50, help="ค่ายิ่งน้อย ไฟล์ยิ่งเล็กลง")
max_dpi = st.sidebar.slider("ขนาดความกว้างสูงสุด (Pixels)", 600, 2000, 1200)

# --- ฟังก์ชันบีบอัด PDF ---
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

# --- ส่วนประมวลผลและดาวน์โหลด ---
if uploaded_file is not None:
    if st.button("🚀 เริ่มบีบอัดไฟล์ PDF", type="primary"):
        with st.spinner("⏳ กำลังบีบอัดไฟล์ PDF..."):
            input_bytes = uploaded_file.read()
            orig_size = len(input_bytes) / (1024 * 1024)
            
            compressed_bytes = compress_pdf_stream(input_bytes, quality, max_dpi)
            comp_size = len(compressed_bytes) / (1024 * 1024)
            
            st.success(f"✅ บีบอัดสำเร็จ! (ขนาดเดิม {orig_size:.2f} MB ➡️ เหลือเพียง {comp_size:.2f} MB)")
            
            # ปุ่มดาวน์โหลดไฟล์
            st.download_button(
                label="📥 ดาวน์โหลดไฟล์ PDF ที่บีบอัดแล้ว",
                data=compressed_bytes,
                file_name=f"compressed_{uploaded_file.name}",
                mime="application/pdf"
            )