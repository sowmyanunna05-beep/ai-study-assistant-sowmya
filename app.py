import streamlit as st
import fitz
import google.generativeai as genai
from datetime import date
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
    genai.configure(
        api_key=st.secrets["GEMINI_API_KEY"]
    )
except Exception:
    st.error("GEMINI_API_KEY is missing in Streamlit Secrets.")
    st.stop()


# Latest/current text models.
# The app tries them in this order and automatically
# moves to the next model if one is unavailable.
MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro"
]


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

# ONE COUNTER ONLY
st.sidebar.title("⚙️ Settings")
st.sidebar.metric(
    "Questions Today",
    f"{st.session_state.q_count}/100"
)

if st.session_state.q_count >= 100:
    st.error("🚫 Today's 100-question limit has been reached.")
    st.info("Please come back tomorrow.")
    st.stop()


# ---------------------------------------------------------
# GEMINI RESPONSE
# ---------------------------------------------------------
def get_answer(prompt):

    last_error = ""

    for model_name in MODELS:

        try:

            model = genai.GenerativeModel(
                model_name
            )

            # Gemini 3.8 / 3.7 / 3.6 / 3.5
            # are used without old sampling settings.
            response = model.generate_content(
                prompt
            )

            if response and response.text:
                return response.text, model_name

        except Exception as e:
            last_error = str(e)
            continue

    raise Exception(
        f"No available Gemini model. Last error: {last_error}"
    )


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

    for i, page in enumerate(document):

        text = page.get_text("text").strip()

        if text:
            pages.append({
                "page": i + 1,
                "text": text
            })

    document.close()

    return pages


# ---------------------------------------------------------
# FIND RELEVANT PAGES
# ---------------------------------------------------------
def find_relevant_pages(question, pages):

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

        # Count occurrences instead of just checking
        # whether the word exists.
        score = sum(
            text.count(word)
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
        for score, page in results[:5]
    ]


# ---------------------------------------------------------
# CREATE CONTEXT
# ---------------------------------------------------------
def create_context(pages):

    return "\n\n".join(
        f"--- PDF PAGE {p['page']} ---\n{p['text']}"
        for p in pages
    )


# ---------------------------------------------------------
# SHOW ACTUAL PDF DIAGRAMS / IMAGES
# ---------------------------------------------------------
def show_pdf_diagrams(pdf_bytes, page_numbers):

    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    found = False

    for page_number in page_numbers:

        if page_number < 1 or page_number > len(document):
            continue

        page = document[page_number - 1]

        # Only extract actual embedded images.
        # Do NOT render the complete PDF page.
        images = page.get_images(full=True)

        for image in images:

            try:

                image_data = document.extract_image(
                    image[0]
                )

                width = image_data.get(
                    "width", 0
                )

                height = image_data.get(
                    "height", 0
                )

                if width >= 100 and height >= 100:

                    st.image(
                        image_data["image"],
                        caption=(
                            f"Diagram/Image from PDF "
                            f"— Page {page_number}"
                        ),
                        use_container_width=True
                    )

                    found = True

            except Exception:
                continue

    document.close()

    return found


# ---------------------------------------------------------
# PDF UPLOAD
# ---------------------------------------------------------
pdf_file = st.file_uploader(
    "📄 Upload your PDF",
    type=["pdf"],
    help="Maximum file size: 1 GB"
)

if not pdf_file:

    st.info(
        "👆 Upload a PDF to start studying."
    )

    st.markdown("""
### 📚 Features

- 📄 PDF-based question answering
- 🎯 Exact answers from uploaded PDF
- 🇬🇧 English-only answers
- 📑 Source page numbers
- 🖼️ PDF diagram/image extraction
- 🤖 Latest Gemini models with fallback
- 🔢 100 questions per day
- 📦 Up to 1 GB PDF
""")

    st.stop()


# ---------------------------------------------------------
# FILE SIZE
# ---------------------------------------------------------
pdf_bytes = pdf_file.getvalue()

MAX_SIZE = 1024 * 1024 * 1024

if len(pdf_bytes) > MAX_SIZE:

    st.error(
        "❌ PDF is larger than 1 GB."
    )

    st.stop()

size_mb = len(pdf_bytes) / (1024 * 1024)

st.info(
    f"📦 PDF Size: {size_mb:.2f} MB"
)


# ---------------------------------------------------------
# READ PDF
# ---------------------------------------------------------
with st.spinner("📖 Reading PDF..."):

    try:

        pages = extract_pdf(
            pdf_bytes
        )

    except Exception as e:

        st.error(
            f"PDF reading error: {e}"
        )

        st.stop()


if not pages:

    st.warning(
        "⚠️ No readable text was found in this PDF."
    )

    st.stop()


st.success(
    f"✅ PDF Ready — {len(pages)} pages processed"
)


# ---------------------------------------------------------
# QUESTION
# ---------------------------------------------------------
question = st.text_input(
    "🔎 Ask your question",
    placeholder="Example: What is Artificial Intelligence?"
)

generate = st.button(
    "🚀 Generate Answer",
    type="primary",
    use_container_width=True
)


if generate:

    if not question.strip():

        st.warning(
            "Please enter a question."
        )

        st.stop()


    if st.session_state.q_count >= 100:

        st.error(
            "Daily question limit reached."
        )

        st.stop()


    # -----------------------------------------------------
    # SEARCH PDF
    # -----------------------------------------------------
    with st.spinner(
        "🔍 Searching your PDF..."
    ):

        relevant_pages = find_relevant_pages(
            question,
            pages
        )


    if not relevant_pages:

        st.warning(
            "❌ The answer is not available in the uploaded PDF."
        )

        st.stop()


    # -----------------------------------------------------
    # CREATE CONTEXT
    # -----------------------------------------------------
    context = create_context(
        relevant_pages
    )

    # Prevent unnecessarily huge prompt
    context = context[:30000]


    # -----------------------------------------------------
    # STRICT PDF-ONLY PROMPT
    # -----------------------------------------------------
    prompt = f"""
You are an AI Study Assistant that answers questions
ONLY from an uploaded PDF.

STRICT RULES:

1. Use ONLY the PDF text provided below.
2. Do NOT use outside knowledge.
3. Do NOT use internet information.
4. Do NOT guess.
5. Do NOT invent facts.
6. Give ONLY the answer needed for the question.
7. Do NOT copy unrelated paragraphs.
8. Do NOT include the PDF front page unless it contains
   information that directly answers the question.
9. Do NOT include unrelated pages.
10. Keep the meaning exactly the same as the PDF.
11. You may simplify the wording for easier understanding.
12. Answer in English only.
13. Include the exact PDF page number containing the answer.
14. If the answer is not present in the supplied PDF text,
    respond exactly:

"The answer is not available in the uploaded PDF."

QUESTION:
{question}

PDF CONTENT:
{context}

OUTPUT FORMAT:

Answer:
[Direct answer based only on the PDF]

Source:
Page [page number]
"""


    # -----------------------------------------------------
    # GENERATE ANSWER
    # -----------------------------------------------------
    st.divider()

    st.subheader(
        "1️⃣ Exact Answer from PDF"
    )

    try:

        with st.spinner(
            "🤖 Generating answer..."
        ):

            answer, model_used = get_answer(
                prompt
            )


        if answer:

            st.write(
                answer
            )

            st.caption(
                f"Model used: {model_used}"
            )

            # Count successful question
            st.session_state.q_count += 1

            # Update the SAME sidebar counter
            st.sidebar.metric(
                "Questions Today",
                f"{st.session_state.q_count}/100"
            )

        else:

            st.warning(
                "No answer was generated."
            )


    except Exception as e:

        st.error(
            f"AI Error: {e}"
        )


    # -----------------------------------------------------
    # SOURCE PAGES
    # -----------------------------------------------------
    st.divider()

    st.subheader(
        "2️⃣ Relevant PDF Pages"
    )

    page_numbers = [
        p["page"]
        for p in relevant_pages
    ]

    st.write(
        "Answer found on page(s):",
        ", ".join(
            map(str, page_numbers)
        )
    )


    # -----------------------------------------------------
    # DIAGRAM
    # -----------------------------------------------------
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
                "No separate embedded diagram/image "
                "was detected on the relevant PDF pages."
            )

    except Exception as e:

        st.warning(
            f"Diagram extraction error: {e}"
        )

   
       
          
   
