import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
from datetime import date
import streamlit.components.v1 as components

st.set_page_config(page_title="AI Study Assistant Pro", page_icon="📚", layout="wide")
st.title("📚 AI Study Assistant")
st.caption("Exact PDF Answer + English Explanation + Auto Diagram | 1GB Support | 100 Q/Day")

# --- GEMINI CONFIG - LATEST MODEL ---
api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)

# --- DAILY LIMIT 100 ---
if "q_count" not in st.session_state:
    st.session_state.q_count = 0
    st.session_state.q_date = str(date.today())

if st.session_state.q_date!= str(date.today()):
    st.session_state.q_count = 0
    st.session_state.q_date = str(date.today())

st.sidebar.title("📊 Usage")
st.sidebar.metric("Today Questions", f"{st.session_state.q_count} / 100")
if st.session_state.q_count >= 100:
    st.error("Daily limit 100 reached. Tomorrow try chey.")
    st.stop()

# --- PDF UPLOAD - 1GB FAST ---
pdf_file = st.file_uploader("📄 PDF Upload Cheyu (Max 1GB)", type="pdf")

if pdf_file:
    file_mb = pdf_file.size / (1024*1024)
    st.info(f"File Size: {file_mb:.2f} MB")

    if file_mb > 1024:
        st.error("1GB kanna ekkuva undi. Konchem compress chey.")
        st.stop()

    @st.cache_data(show_spinner=False)
    def get_pdf_text(file):
        reader = PdfReader(file)
        text = ""
        # Fast kosam first 40 pages only - 1GB ayina 15 sec lo aipothundi
        pages_to_read = min(len(reader.pages), 40)
        for i in range(pages_to_read):
            try:
                t = reader.pages[i].extract_text()
                if t:
                    text += t + "\n"
            except:
                continue
        return text

    with st.spinner("📖 PDF Fast ga chaduvutunna..."):
        pdf_text = get_pdf_text(pdf_file)

    st.success(f"✅ PDF Ready! {len(pdf_text)} characters read.")

    question = st.text_input("❓ Question Adugu (English lo)")

    if st.button("🚀 Generate Answer") and question:
        if len(question.strip()) < 3:
            st.warning("Question konchem peddaga adugu")
            st.stop()

        st.session_state.q_count += 1

        # --- PART 1: EXACT ANSWER FROM PDF ---
        st.divider()
        st.subheader("1️⃣ Exact Answer from PDF (Same to Same - For Exam)")
        keywords = [w.lower() for w in question.split() if len(w) > 3]
        found = []
        for line in pdf_text.split("\n"):
            clean = line.strip()
            if len(clean) < 30:
                continue
            if any(k in clean.lower() for k in keywords):
                found.append(clean)

        if found:
            for l in found[:6]:
                st.write(f"▪️ {l}")
        else:
            st.write("Exact match ee 40 pages lo dorakaledu, kindha explanation chudu.")

        # --- PART 2 & 3: EXPLANATION + AUTO DIAGRAM ---
        st.divider()
        st.subheader("2️⃣ Simple Explanation (In English)")
        st.subheader("3️⃣ Related Diagram (Auto Generated)")

        try:
            # LATEST MODEL - 200/day free, fastest
            model = genai.GenerativeModel("gemini-2.0-flash-lite")

            prompt = f"""
            You are a study assistant.
            PDF Content: {pdf_text[:8000]}
            Question: {question}

            Instructions:
            1. First, give Simple English explanation in 5-6 bullet points.
            2. Then, give a RELATED diagram using mermaid syntax ONLY.
            Format strictly like this:
            EXPLANATION:
            - point1
            - point2
            DIAGRAM:
            ```mermaid
            graph TD
            A[Topic] --> B[Concept1]
            A --> C[Concept2]
