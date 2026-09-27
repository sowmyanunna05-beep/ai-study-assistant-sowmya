import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
from datetime import date
import fitz # PyMuPDF - PDF lo image teeyadaniki

st.set_page_config(page_title="AI Study Assistant", page_icon="📚", layout="wide")
st.title("📚 AI Study Assistant - Exact PDF Diagram")
st.caption("Exact Text + Exact Diagram from PDF | 1GB | 100 Q/Day")

api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)

# --- 100 Q LIMIT ---
if "q_count" not in st.session_state:
    st.session_state.q_count = 0
    st.session_state.q_date = str(date.today())
if st.session_state.q_date!= str(date.today()):
    st.session_state.q_count = 0
    st.session_state.q_date = str(date.today())

st.sidebar.metric("Today Usage", f"{st.session_state.q_count} / 100")
if st.session_state.q_count >= 100:
    st.error("100 limit over")
    st.stop()

# --- PDF UPLOAD ---
pdf_file = st.file_uploader("PDF Upload (Max 1GB)", type="pdf")

if pdf_file:
    file_mb = pdf_file.size / (1024*1024)
    st.info(f"File Size: {file_mb:.1f} MB")

    # PDF bytes save chesukovali images kosam
    pdf_bytes = pdf_file.getvalue()

    @st.cache_data
    def get_pdf_data(pdf_bytes):
        reader = PdfReader(pdf_file)
        text = ""
        pages_with_text = {}
        for i in range(min(len(reader.pages), 50)):
            try:
                t = reader.pages[i].extract_text()
                if t:
                    text += t + "\n"
                    pages_with_text[i] = t
            except:
                pass
        return text, pages_with_text

    with st.spinner("Reading PDF..."):
        pdf_text, pages_text = get_pdf_data(pdf_bytes)

    st.success("PDF Ready!")

    q = st.text_input("Question Adugu - Ex: What is Naive Bayes?")

    if st.button("🚀 Generate Exact Answer") and q:
        st.session_state.q_count += 1
        keywords = [w.lower() for w in q.split() if len(w) > 3]

        # --- PART 1: EXACT TEXT ---
        st.divider()
        st.subheader("1️⃣ Exact Answer from PDF (Same to Same)")
        found_pages = []
        found_lines = []
        for p_no, p_text in pages_text.items():
            for line in p_text.split("\n"):
                if len(line.strip()) > 30 and any(k in line.lower() for k in keywords):
                    found_lines.append(f"Page {p_no+1}: {line.strip()}")
                    if p_no not in found_pages:
                        found_pages.append(p_no)

        if found_lines:
            for l in found_lines[:8]:
                st.write(f"▪️ {l}")
        else:
            st.write("Exact text ee 50 pages lo dorakaledu")
            found_pages = list(pages_text.keys())[:3] # first 3 pages diagrams chupiddam

        # --- PART 2: SIMPLE EXPLANATION ---
        st.divider()
        st.subheader("2️⃣ Simple Explanation (English)")
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-lite")
            prompt = f"Explain simple English in 5 points: Q={q} PDF={pdf_text[:6000]}"
            res = model.generate_content(prompt)
            st.write(res.text)
        except Exception as e:
            st.error(f"AI Error: {e}")

        # --- PART 3: EXACT DIAGRAM FROM PDF ---
        st.divider()
        st.subheader("3️⃣ Exact Diagram from PDF (Original)")
        st.write(f"Question ki related pages: {found_pages} - vatilo diagrams unte chupistunna...")

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            diagram_found = False

            # Related pages lo images vethukutam
            pages_to_check = found_pages if found_pages else range(min(len(doc), 10))

            for p_no in pages_to_check:
                page = doc[p_no]
                images = page.get_images(full=True)

                if images:
                    for img_index, img in enumerate(images):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]

                        # Diagram size check - chinna icons kadu, pedda diagrams mathrame
                        if base_image["width"] > 150 and base_image["height"] > 150:
                            st.image(image_bytes, caption=f"Exact Diagram from Page {p_no+1} - From Your PDF", use_column_width=True)
                            diagram_found = True

                # Page ni full screenshot la kuda chupinchachu - diagram text tho unte
                if not diagram_found and p_no in found_pages:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # High quality
                    st.image(pix.tobytes("png"), caption=f"Full Page {p_no+1} Screenshot (Diagram with text) - Exact from PDF", use_column_width=True)
                    diagram_found = True
                    break

            if not diagram_found:
                st.warning("Ee pages lo extract cheyagalige diagram image ledu. PDF scanned ayite image raadu. Text diagrams ayite Part 1 lo vachayi.")
                st.info("Tip: PDF lo diagram photo la unte ne exact vastundi. Text diagram ayite adi text lone vastundi.")

        except Exception as e:
            st.error(f"Diagram extract error: {e}. PyMuPDF install ayyinda check chey.")

else:
    st.info("👆 PDF upload chey, exact diagram vastundi")
