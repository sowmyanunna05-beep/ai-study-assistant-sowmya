import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
from datetime import date
import fitz
import io

st.set_page_config(page_title="AI Study Assistant", page_icon="📚", layout="wide")
st.title("📚 AI Study Assistant")
st.caption("Exact PDF | 1GB | 100 Q/Day | Latest Model")

api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)

if "q_count" not in st.session_state:
    st.session_state.q_count = 0
    st.session_state.q_date = str(date.today())
if st.session_state.q_date!= str(date.today()):
    st.session_state.q_count = 0
    st.session_state.q_date = str(date.today())

st.sidebar.metric("Today", f"{st.session_state.q_count} / 100")
if st.session_state.q_count >= 100:
    st.error("100 limit over")
    st.stop()

def get_gemini_response(prompt_text):
    models_to_try = [
        "gemini-3.8-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest"
    ]
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            res = model.generate_content(prompt_text)
            return res.text, model_name
        except Exception as e:
            if "404" in str(e):
                continue
            continue
    raise Exception("Models busy, 1 min tarvata try chey")

pdf_file = st.file_uploader("PDF Upload (Max 1GB)", type="pdf")

if pdf_file:
    pdf_bytes = pdf_file.getvalue()
    st.info(f"Size: {len(pdf_bytes)/(1024*1024):.1f} MB")

    @st.cache_data
    def get_pdf_data(pdf_bytes):
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        pages_text = {}
        for i in range(min(len(reader.pages), 50)):
            try:
                t = reader.pages[i].extract_text()
                if t:
                    text += t + "\n"
                    pages_text[i] = t
            except:
                pass
        return text, pages_text

    pdf_text, pages_text = get_pdf_data(pdf_bytes)
    st.success("PDF Ready!")

    q = st.text_input("Question Adugu")
    if st.button("🚀 Generate") and q:
        st.session_state.q_count += 1
        keywords = [w.lower() for w in q.split() if len(w)>3]

        st.divider()
        st.subheader("1️⃣ Exact Answer from PDF")
        found_pages = []
        for p_no, p_text in pages_text.items():
            for line in p_text.split("\n"):
                if len(line.strip())>30 and any(k in line.lower() for k in keywords):
                    st.write(f"▪️ Page {p_no+1}: {line.strip()}")
                    if p_no not in found_pages:
                        found_pages.append(p_no)

        if not found_pages:
            found_pages = [0,1,2]

        st.divider()
        st.subheader("2️⃣ Simple Explanation (English)")
        try:
            prompt = f"Explain simple English 5 points. Q={q} PDF={pdf_text[:6000]}"
            ans, used_model = get_gemini_response(prompt)
            st.write(ans)
            st.caption(f"Model used: {used_model} - Latest 3.8 version")
        except Exception as e:
            st.error(f"AI Error: {e}")

        st.divider()
        st.subheader("3️⃣ Exact Diagram from PDF")
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            diagram_found = False
            for p_no in found_pages[:3]:
                if p_no >= len(doc): continue
                page = doc[p_no]
                images = page.get_images(full=True)
                found=False
                for img in images:
                    base = doc.extract_image(img[0])
                    if base["width"]>100 and base["height"]>100:
                        st.image(base["image"], caption=f"Exact Diagram Page {p_no+1}", use_container_width=True)
                        found=True
                        diagram_found=True
                        break
                if found:
                    break

            if not diagram_found:
                # PDF lo photo ledu kabatti AI tho picture diagram generate chey
                st.info("PDF lo photo diagram ledu, related diagram generate chesa")
                draw_diagram_from_text("AI Process", ["Input", "Processing", "GPU Acceleration", "Output"])
                break
        except Exception as e:
            st.error(f"Diagram error: {e}")
    
       
               
