import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
from datetime import date
import io
import re

# ---------------------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="📚",
    layout="wide"
)

st.title("📚 AI Study Assistant")
st.caption("PDF-based answers • English • Diagram support • 100 Questions/Day")

# ---------------------------------------------------------
# GEMINI API
# ---------------------------------------------------------
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("GEMINI_API_KEY is missing. Add it in Streamlit Secrets.")
    st.stop()

# ---------------------------------------------------------
# DAILY QUESTION LIMIT
# ---------------------------------------------------------
TODAY = str(date.today())

if "q_count" not in st.session_state:
    st.session_state.q_count = 0
    st.session_state.q_date = TODAY

if st.session_state.q_date != TODAY:
    st.session_state.q_count = 0
    st.session_state.q_date = TODAY

st.sidebar.title("⚙️ Settings")
st.sidebar.metric(
    "Questions Today",
    f"{st.session_state.q_count} / 100"
)

if st.session_state.q_count >= 100:
    st.error("🚫 Today's 100-question limit has been reached.")
    st.info("Please come back tomorrow.")
    st.stop()

# ---------------------------------------------------------
# GEMINI MODEL
# ---------------------------------------------------------
def get_gemini_response(prompt_text):

    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash"
    ]

    last_error = ""

    for model_name in models_to_try:

        try:
            model = genai.GenerativeModel(model_name)

            response = model.generate_content(
                prompt_text
            )

            if response and response.text:
                return response.text, model_name

        except Exception as e:

            last_error = str(e)

            # Try next model
            continue

    raise Exception(
        f"No available Gemini model. Last error: {last_error}"
    )
    

    last_error = None

    for model_name in models:
        try:
            model = genai.GenerativeModel(model_name)

            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "max_output_tokens": 1500
                }
            )

            if response and response.text:
                return response.text, model_name

        except Exception as e:
            last_error = e

    raise Exception(f"AI model error: {last_error}")


# ---------------------------------------------------------
# PDF EXTRACTION
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def extract_pdf(pdf_bytes):

    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    pages = []

    for page_number in range(len(document)):

        page = document[page_number]

        text = page.get_text("text")

        if text.strip():
            pages.append({
                "page": page_number + 1,
                "text": text
            })

    document.close()

    return pages


# ---------------------------------------------------------
# FIND RELEVANT PAGES
# ---------------------------------------------------------
def find_relevant_pages(question, pages):

    question_words = set(
        word.lower()
        for word in re.findall(r"[A-Za-z0-9]+", question)
        if len(word) > 2
    )

    scored_pages = []

    for page in pages:

        text = page["text"].lower()

        score = 0

        for word in question_words:
            if word in text:
                score += 1

        if score > 0:
            scored_pages.append(
                (score, page)
            )

    scored_pages.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        page
        for score, page in scored_pages[:8]
    ]


# ---------------------------------------------------------
# CREATE CONTEXT
# ---------------------------------------------------------
def create_context(relevant_pages):

    context = ""

    for page in relevant_pages:

        context += (
            f"\n\n--- PDF PAGE {page['page']} ---\n"
        )

        context += page["text"]

    return context


# ---------------------------------------------------------
# DIAGRAM EXTRACTION
# ---------------------------------------------------------
def show_pdf_diagrams(pdf_bytes, page_numbers):

    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    diagram_found = False

    for page_number in page_numbers:

        index = page_number - 1

        if index < 0 or index >= len(document):
            continue

        page = document[index]

        # First check embedded images
        images = page.get_images(full=True)

        for image in images:

            try:
                image_data = document.extract_image(
                    image[0]
                )

                width = image_data.get("width", 0)
                height = image_data.get("height", 0)

                if width >= 100 and height >= 100:

                    st.image(
                        image_data["image"],
                        caption=f"Diagram/Image from PDF — Page {page_number}",
                        use_container_width=True
                    )

                    diagram_found = True

            except Exception:
                continue

        # If no embedded image, render page as image
        if not images:

            pix = page.get_pixmap(
                matrix=fitz.Matrix(1.5, 1.5)
            )

            image_bytes = pix.tobytes("png")

            st.image(
                image_bytes,
                caption=f"PDF Page {page_number}",
                use_container_width=True
            )

            diagram_found = True

    document.close()

    return diagram_found


# ---------------------------------------------------------
# PDF UPLOAD
# ---------------------------------------------------------
pdf_file = st.file_uploader(
    "📄 Upload your PDF",
    type=["pdf"],
    help="Maximum recommended file size: 1 GB"
)

if pdf_file:

    pdf_bytes = pdf_file.getvalue()

    size_mb = len(pdf_bytes) / (1024 * 1024)

    st.info(
        f"📦 PDF Size: {size_mb:.2f} MB"
    )

    # -----------------------------------------------------
    # 1 GB CHECK
    # -----------------------------------------------------
    MAX_SIZE = 1024 * 1024 * 1024

    if len(pdf_bytes) > MAX_SIZE:

        st.error(
            "❌ File is larger than 1 GB."
        )

        st.stop()

    # -----------------------------------------------------
    # EXTRACT PDF
    # -----------------------------------------------------
    with st.spinner("📖 Reading PDF..."):

        try:

            pages = extract_pdf(pdf_bytes)

        except Exception as e:

            st.error(
                f"PDF reading error: {e}"
            )

            st.stop()

    if not pages:

        st.warning(
            "⚠️ No readable text was found in this PDF."
        )

    else:

        st.success(
            f"✅ PDF Ready — {len(pages)} pages processed"
        )

        # -------------------------------------------------
        # QUESTION
        # -------------------------------------------------
        question = st.text_input(
            "🔎 Ask your question",
            placeholder="Example: What is Artificial Intelligence?"
        )

        generate = st.button(
            "🚀 Generate Answer",
            type="primary",
            use_container_width=True
        )

        if generate and question.strip():

            # -------------------------------------------------
            # DAILY COUNT
            # -------------------------------------------------
            if st.session_state.q_count >= 100:

                st.error(
                    "Daily question limit reached."
                )

                st.stop()

            st.session_state.q_count += 1

            # -------------------------------------------------
            # FIND PAGES
            # -------------------------------------------------
            with st.spinner(
                "🔍 Searching your PDF..."
            ):

                relevant_pages = find_relevant_pages(
                    question,
                    pages
                )

            # -------------------------------------------------
            # NO MATCH
            # -------------------------------------------------
            if not relevant_pages:

                st.warning(
                    "❌ The answer could not be found in the uploaded PDF."
                )

                st.info(
                    "Please ask a question related to the PDF."
                )

                st.stop()

            # -------------------------------------------------
            # CONTEXT
            # -------------------------------------------------
            context = create_context(
                relevant_pages
            )

            # -------------------------------------------------
            # LIMIT CONTEXT SIZE
            # -------------------------------------------------
            context = context[:30000]

            # -------------------------------------------------
            # PROMPT
            # -------------------------------------------------
            prompt = f"""
You are an AI Study Assistant.

IMPORTANT RULES:

1. Answer ONLY using the information provided in the PDF context.
2. Do NOT use outside knowledge.
3. Do NOT invent facts.
4. Do NOT add information that is not present in the PDF.
5. Answer in English only.
6. Keep the meaning of the PDF exactly the same.
7. You may simplify grammar, but do not change the meaning.
8. If the answer is not present in the PDF, say exactly:

"The answer is not available in the uploaded PDF."

9. Mention the relevant PDF page number.
10. If the PDF contains a list, definition, process, advantages,
    disadvantages, or steps, preserve the important points.
11. Do not say that you searched the internet.

QUESTION:
{question}

PDF CONTEXT:
{context}

Answer format:

Answer:
[Answer based only on the PDF]

Source:
Page [page number]
"""

            # -------------------------------------------------
            # AI ANSWER
            # -------------------------------------------------
            st.divider()

            st.subheader(
                "1️⃣ Exact Answer from PDF"
            )

            try:

                with st.spinner(
                    "🤖 Generating answer..."
                ):

                    answer, model_used = get_gemini_response(
                        prompt
                    )

                st.write(answer)

                st.caption(
                    f"Model: {model_used}"
                )

            except Exception as e:

                st.error(
                    f"AI Error: {e}"
                )

            # -------------------------------------------------
            # SOURCE PAGES
            # -------------------------------------------------
            st.divider()

            st.subheader(
                "2️⃣ Relevant PDF Pages"
            )

            page_numbers = [
                page["page"]
                for page in relevant_pages
            ]

            st.write(
                "Relevant pages:",
                ", ".join(
                    str(p)
                    for p in page_numbers
                )
            )

            # -------------------------------------------------
            # DIAGRAMS
            # -------------------------------------------------
            st.divider()

            st.subheader(
                "3️⃣ Diagram / PDF Visual"
            )

            try:

                diagram_found = show_pdf_diagrams(
                    pdf_bytes,
                    page_numbers[:3]
                )

                if not diagram_found:

                    st.info(
                        "No separate image/diagram was detected "
                        "on the relevant PDF pages."
                    )

            except Exception as e:

                st.warning(
                    f"Diagram extraction error: {e}"
                )

            # -------------------------------------------------
           

else:

    st.info(
        "👆 Upload a PDF to start studying."
    )

    st.markdown(
        """
### 📚 Features

- 📄 PDF-based question answering
- 🎯 Answers restricted to uploaded PDF
- 🇬🇧 English-only responses
- 📑 Page references
- 🖼️ PDF diagram/image extraction
- ⚡ Fast Gemini model
- 🔢 100 questions per day
- 📦 Up to 1 GB PDF
"""
    )
   
   



