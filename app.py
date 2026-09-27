import streamlit as st
import fitz
import google.generativeai as genai
import re
from datetime import date

# ---------------- PAGE ----------------
st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="📚",
    layout="wide"
)

st.title("📚 AI Study Assistant")
st.caption("PDF-based answers • English • Diagram support • 100 Questions/Day")

# ---------------- GEMINI ----------------
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("GEMINI_API_KEY is missing in Streamlit Secrets.")
    st.stop()

  models_to_try = (
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash"
  )

# ---------------- DAILY LIMIT ----------------
today = str(date.today())

if "count" not in st.session_state:
    st.session_state.count = 0
    st.session_state.day = today

if st.session_state.day != today:
    st.session_state.count = 0
    st.session_state.day = today

st.sidebar.title("⚙️ Settings")
st.sidebar.metric("Questions Today", f"{st.session_state.count} / 100")

if st.session_state.count >= 100:
    st.error("🚫 Today's 100-question limit has been reached.")
    st.stop()

# ---------------- PDF READER ----------------
def read_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []

    for i, page in enumerate(doc):
        text = page.get_text("text").strip()

        if text:
            pages.append({
                "page": i + 1,
                "text": text
            })

    doc.close()
    return pages


# ---------------- FIND RELEVANT PAGES ----------------
def find_pages(question, pages, limit=5):

    words = {
        w.lower()
        for w in re.findall(r"[A-Za-z0-9]+", question)
        if len(w) > 2
    }

    results = []

    for page in pages:
        text = page["text"].lower()
        score = sum(word in text for word in words)

        if score:
            results.append((score, page))

    results.sort(reverse=True, key=lambda x: x[0])

    return [page for score, page in results[:limit]]


# ---------------- SHOW DIAGRAMS ONLY ----------------
def show_diagrams(pdf_bytes, page_numbers):

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    found = False

    for number in page_numbers:
        page = doc[number - 1]

        for img in page.get_images(full=True):

            try:
                data = doc.extract_image(img[0])

                if data["width"] >= 100 and data["height"] >= 100:
                    st.image(
                        data["image"],
                        caption=f"Diagram/Image — Page {number}",
                        use_container_width=True
                    )
                    found = True

            except:
                pass

    doc.close()
    return found


# ---------------- UPLOAD ----------------
pdf_file = st.file_uploader(
    "📄 Upload your PDF",
    type="pdf"
)

if not pdf_file:

    st.info("👆 Upload a PDF to start studying.")

    st.markdown("""
### 📚 Features

- 📄 PDF-based question answering
- 🎯 Answers only from uploaded PDF
- 🇬🇧 English answers
- 📑 Page references
- 🖼️ Diagram/image extraction
- 🤖 Gemini AI
- 🔢 100 questions per day
- 📦 Up to 1 GB PDF
""")

    st.stop()


# ---------------- PROCESS PDF ----------------
pdf_bytes = pdf_file.getvalue()

if len(pdf_bytes) > 1024 * 1024 * 1024:
    st.error("❌ PDF is larger than 1 GB.")
    st.stop()

with st.spinner("📖 Reading PDF..."):
    pages = read_pdf(pdf_bytes)

if not pages:
    st.error("⚠️ No readable text found in this PDF.")
    st.stop()

st.success(f"✅ PDF Ready — {len(pages)} pages processed")


# ---------------- QUESTION ----------------
question = st.text_input(
    "🔎 Ask your question",
    placeholder="Example: What is Artificial Intelligence?"
)

if st.button(
    "🚀 Generate Answer",
    type="primary",
    use_container_width=True
):

    if not question.strip():
        st.warning("Please enter a question.")
        st.stop()

    if st.session_state.count >= 100:
        st.error("Daily question limit reached.")
        st.stop()

    st.session_state.count += 1

    # Find only relevant pages
    with st.spinner("🔍 Searching your PDF..."):
        relevant = find_pages(question, pages)

    if not relevant:
        st.warning(
            "❌ The answer is not available in the uploaded PDF."
        )
        st.stop()

    # Create small context
    context = "\n\n".join(
        f"PDF PAGE {p['page']}:\n{p['text']}"
        for p in relevant
    )

    context = context[:30000]

    # ---------------- AI PROMPT ----------------
    prompt = f"""
You are an AI Study Assistant.

Answer the question ONLY using the PDF context below.

Rules:
- Use only information from the PDF.
- Do not use outside knowledge.
- Do not invent information.
- Answer in English.
- Give the exact information needed for the question.
- Do not repeat unrelated PDF content.
- Do not include the PDF front page unless it contains the answer.
- If the answer is not present, say:
"The answer is not available in the uploaded PDF."
- Mention the page number containing the answer.

QUESTION:
{question}

PDF CONTEXT:
{context}

Give the answer in this format:

Answer:
[Answer]

Source:
Page [number]
"""

    # ---------------- GENERATE ----------------
    st.divider()
    st.subheader("1️⃣ Exact Answer from PDF")

    try:

        with st.spinner("🤖 Generating answer..."):

            model = genai.GenerativeModel(MODEL)

            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 1200
                }
            )

        st.write(response.text)
        st.caption(f"Model: {MODEL}")

    except Exception as e:
        st.error(f"AI Error: {e}")

    # ---------------- SOURCE ----------------
    st.divider()
    st.subheader("2️⃣ Relevant PDF Pages")

    numbers = [p["page"] for p in relevant]

    st.write(
        "Relevant pages:",
        ", ".join(map(str, numbers))
    )

    # ---------------- DIAGRAMS ----------------
    st.divider()
    st.subheader("3️⃣ Diagram / PDF Visual")

    if not show_diagrams(pdf_bytes, numbers[:3]):
        st.info(
            "No separate diagram/image was detected "
            "on the relevant pages."
        )

    # ---------------- COUNT ----------------
    st.sidebar.metric(
        "Questions Today",
        f"{st.session_state.count} / 100"
    )

           

                   
          
                  
