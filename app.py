import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai

st.set_page_config(page_title="AI Study Assistant", page_icon="📚")
st.title("📚 AI Study Assistant")

api_key = st.secrets["GEMINI_API_KEY"]
pdf_file = st.file_uploader("PDF Upload Cheyu", type="pdf")

if pdf_file:
    genai.configure(api_key=api_key)
    
    # Auto model finder - 3 models try chestundi, edhi work ayithe adhi
    model_names = ["models/gemini-3.8-flash", "models/gemini-pro", "gemini-3.8-flash"]
    model = None
    for m_name in model_names:
        try:
            model = genai.GenerativeModel(m_name)
            break
        except:
            continue
    if model is None:
        model = genai.GenerativeModel("gemini-pro")

    reader = PdfReader(pdf_file)
    pdf_text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            pdf_text = pdf_text + t + "\n"

    st.success("PDF Ready!")
    question = st.text_input("Ask your question from PDF")

    if st.button("Generate Answer"):
        st.subheader("1. Exact Text from PDF (Same to Same):")
        keys = question.lower().split()
        found = []
        for line in pdf_text.split("\n"):
            for k in keys:
                if len(k)>2 and k in line.lower() and len(line.strip())>20:
                    found.append(line.strip())
                    break
        if found:
            for f in found[:10]:
                st.write("- " + f)
        else:
            st.write(pdf_text[:1500])

        st.subheader("2. Simple English Explanation:")
        try:
            prompt2 = "Explain in simple ENGLISH 5 points: " + question + " PDF context: " + pdf_text[:8000]
            res = model.generate_content(prompt2)
            st.write(res.text)
        except Exception as e:
            st.warning("AI busy, but exact PDF text paine undi!")
            st.write(f"Error: {e}")

        if "diagram" in question.lower():
            st.subheader("3. Related Diagram")
            q = question.lower()
            if "autoencoder" in q:
                st.graphviz_chart('digraph { rankdir=LR; Input -> Encoder -> Code -> Decoder -> Output; Code [shape=circle fillcolor=yellow style=filled]; }')
            elif "boltzmann" in q:
                st.graphviz_chart('digraph { rankdir=TB; v1 -> h1; v1 -> h2; v2 -> h1; v2 -> h2; }')
            else:
                st.graphviz_chart('digraph { Input -> Process -> Output; }')
