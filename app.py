import streamlit as st
import fitz
import google.generativeai as genai
import re
from datetime import date

# =====================================================
# PAGE SETTINGS
# =====================================================
st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="📚",
    layout="wide"
)

st.title("📚 AI Study Assistant")
st.caption(
    "PDF-based answers • English • Diagram support • 100 Questions/Day"
)

# =====================================================
# GEMINI API
# =====================================================
try:
    genai.configure(
        api_key=st.secrets["GEMINI_API_KEY"]
    )
except Exception:
    st.error(
        "GEMINI_API_KEY is missing. "
        "Add it in Streamlit Secrets."
    )
    st.stop()


# =====================================================
# GEMINI MODELS
# Newest → older fallback
# =====================================================
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-pro"
]


# =====================================================
# GEMINI RESPONSE
# =====================================================
def generate_answer(prompt):

    last_error = ""

    for model_name in GEMINI_MODELS:

        try:

            model = genai.GenerativeModel(
                model_name
            )

            response = model.generate_content(
                prompt
            )

            if response and response.text:

                return (
                    response.text,
                    model_name
                )

        except Exception as e:

            last_error = str(e)
            continue

    raise Exception(
        "No available Gemini model.\n"
        + last_error
    )


# =====================================================
# DAILY QUESTION LIMIT
# =====================================================
today = str(date.today())

if "count" not in st.session_state:
    st.session_state.count = 0
    st.session_state.day = today

if st.session_state.day != today:

    st.session_state.count = 0
    st.session_state.day = today


# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.title("⚙️ Settings")

st.sidebar.metric(
    "Questions Today",
    f"{st.session_state.count} / 100"
)

if st.session_state.count >= 100:

    st.error(
        "🚫 Today's 100-question limit has been reached."
    )

    st.info(
        "Please come back tomorrow."
    )

    st.stop()


# =====================================================
# READ PDF
# =====================================================
@st.cache_data(show_spinner=False)
def read_pdf(pdf_bytes):

    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    pages = []

    for i, page in enumerate(doc):

        text = page.get_text(
            "text"
        ).strip()

        if text:

            pages.append({
                "page": i + 1,
                "text": text
            })

    doc.close()

    return pages


# =====================================================
# FIND RELEVANT PAGES
# =====================================================
def find_relevant_pages(
    question,
    pages,
    limit=5
):

    words = {
        word.lower()
        for word in re.findall(
            r"[A-Za-z0-9]+",
            question
        )
        if len(word) > 2
    }

    results = []

    for page in pages:

        text = page["text"].lower()

        score = sum(
            word in text
            for word in words
        )

        if score > 0:

            results.append(
                (score, page)
            )

    results.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        page
        for score, page in results[:limit]
    ]


# =====================================================
# SHOW ONLY ACTUAL PDF IMAGES
# =====================================================
def show_diagrams(
    pdf_bytes,
    page_numbers
):

    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    found = False

    for number in page_numbers:

        if number < 1 or number > len(doc):
            continue

        page = doc[number - 1]

        images = page.get_images(
            full=True
        )

        for image in images:

            try:

                data = doc.extract_image(
                    image[0]
                )

                width = data.get(
                    "width",
                    0
                )

                height = data.get(
                    "height",
                    0
                )

                if (
                    width >= 100
                    and height >= 100
                ):

                    st.image(
                        data["image"],
                        caption=(
                            f"Diagram/Image — "
                            f"Page {number}"
                        ),
                        use_container_width=True
                    )

                    found = True

            except Exception:
                pass

    doc.close()

    return found


# =====================================================
# PDF UPLOAD
# =====================================================
pdf_file = st.file_uploader(
    "📄 Upload your PDF",
    type=["pdf"],
    help="Maximum file size: 1 GB"
)


# =====================================================
# NO PDF
# =====================================================
if not pdf_file:

    st.info(
        "👆 Upload a PDF to start studying."
    )

    st.markdown(
        """
### 📚 Features

- 📄 PDF-based question answering
- 🎯 Answers only from uploaded PDF
- 🇬🇧 English answers
- 📑 Relevant page references
- 🖼️ PDF diagram/image extraction
- 🤖 Multiple Gemini models
- ⚡ Automatic model fallback
- 🔢 100 questions per day
- 📦 Up to 1 GB PDF
"""
    )

    st.stop()


# =====================================================
# FILE SIZE
# =====================================================
pdf_bytes = pdf_file.getvalue()

MAX_SIZE = 1024 * 1024 * 1024

if len(pdf_bytes) > MAX_SIZE:

    st.error(
        "❌ PDF is larger than 1 GB."
    )

    st.stop()


# =====================================================
# PROCESS PDF
# =====================================================
with st.spinner(
    "📖 Reading PDF..."
):

    try:

        pages = read_pdf(
            pdf_bytes
        )

    except Exception as e:

        st.error(
            f"PDF reading error: {e}"
        )

        st.stop()


if not pages:

    st.error(
        "⚠️ No readable text was found "
        "in this PDF."
    )

    st.stop()


st.success(
    f"✅ PDF Ready — "
    f"{len(pages)} pages processed"
)


# =====================================================
# QUESTION
# =====================================================
question = st.text_input(
    "🔎 Ask your question",
    placeholder=(
        "Example: What is Artificial Intelligence?"
    )
)


generate = st.button(
    "🚀 Generate Answer",
    type="primary",
    use_container_width=True
)


# =====================================================
# GENERATE ANSWER
# =====================================================
if generate:

    if not question.strip():

        st.warning(
            "Please enter a question."
        )

        st.stop()


    if st.session_state.count >= 100:

        st.error(
            "Daily question limit reached."
        )

        st.stop()


    # -------------------------------------------------
    # SEARCH PDF
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
            "❌ The answer is not available "
            "in the uploaded PDF."
        )

        st.stop()


    # Count valid question
    st.session_state.count += 1


    # -------------------------------------------------
    # CREATE CONTEXT
    # -------------------------------------------------
    context = "\n\n".join(

        f"PDF PAGE {page['page']}:\n"
        f"{page['text']}"

        for page in relevant_pages
    )


    # Keep context manageable
    context = context[:30000]


    # -------------------------------------------------
    # AI PROMPT
    # -------------------------------------------------
    prompt = f"""
You are an AI Study Assistant.

Your job is to answer the user's question
using ONLY the uploaded PDF.

IMPORTANT RULES:

1. Use ONLY information from the PDF.
2. Do NOT use outside knowledge.
3. Do NOT invent facts.
4. Answer in English only.
5. Give ONLY information relevant to the question.
6. Do NOT include unrelated PDF content.
7. Do NOT include the PDF front page unless
   it contains the answer.
8. Do NOT show or reproduce extra PDF pages.
9. Keep the answer clear and easy to understand.
10. Preserve important points from the PDF.
11. If the answer is not available in the PDF,
    say exactly:

"The answer is not available in the uploaded PDF."

12. Mention the page number where the answer
    was found.

QUESTION:
{question}

PDF CONTEXT:
{context}

Give the response in this format:

Answer:
[Relevant answer from the PDF]

Source:
Page [number]
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

            answer, model_used = generate_answer(
                prompt
            )


        if answer:

            st.write(answer)

            st.caption(
                f"🤖 Model used: {model_used}"
            )

        else:

            st.warning(
                "No answer was generated."
            )


    except Exception as e:

        st.error(
            f"AI Error: {e}"
        )


    # -------------------------------------------------
    # RELEVANT PAGES
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
            map(str, page_numbers)
        )
    )


    # -------------------------------------------------
    # DIAGRAMS
    # -------------------------------------------------
    st.divider()

    st.subheader(
        "3️⃣ Diagram / PDF Visual"
    )

    diagram_found = show_diagrams(
        pdf_bytes,
        page_numbers[:3]
    )

    if not diagram_found:

        st.info(
            "No separate diagram/image was "
            "detected on the relevant pages."
        )


    # -------------------------------------------------
    # UPDATE QUESTION COUNT
    # -------------------------------------------------
    st.sidebar.metric(
        "Questions Today",
        f"{st.session_state.count} / 100"
    )
