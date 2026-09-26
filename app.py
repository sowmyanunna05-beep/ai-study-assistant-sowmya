import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai

st.set_page_config(page_title="AI Study Assistant", page_icon="📚")
st.title("📚 AI Study Assistant - Sowmya")

api_key = st.secrets["GEMINI_API_KEY"]
pdf_file = st.file_uploader("PDF Upload Cheyu", type="pdf")

if pdf_file:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    
    reader = PdfReader(pdf_file)
    pdf_text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            pdf_text = pdf_text + t + "\n"
    
    st.success("PDF Ready!")
    question = st.text_input("Question adugu (ex: autoencoder)")
    
    if st.button("Answer Kavali"):
        # 1. PDF LO SAME TEXT SEARCH
        st.subheader("1. Exact Text from PDF (Same to Same):")
        keywords = question.lower().replace("diagram","").strip().split()
        found_lines = []
        for line in pdf_text.split("\n"):
            for k in keywords:
                if k in line.lower() and len(line.strip()) > 20:
                    found_lines.append(line.strip())
                    break
        
        if found_lines:
            for line in found_lines[:8]:
                st.write("- " + line)
        else:
            st.warning("Exact keyword PDF lo dorakaledu, kani related content kindha undi.")
            st.write(pdf_text[:1000])

        # 2. ENGLISH EXPLANATION + DIAGRAM
        st.subheader("2. Simple English Explanation:")
        prompt2 = "Explain in simple ENGLISH 5 points: " + question + " Context: " + pdf_text[:8000]
        res = model.generate_content(prompt2)
        st.write(res.text)

        if "diagram" in question.lower():
            st.subheader("3. Related Diagram:")
            q = question.lower()
            if "autoencoder" in q:
                st.graphviz_chart('digraph { rankdir=LR; Input -> Encoder -> Code -> Decoder -> Output; Code [label="Bottleneck" shape=circle fillcolor=yellow style=filled]; }')
            elif "boltzmann" in q:
                st.graphviz_chart('digraph { rankdir=TB; v1 -> h1; v1 -> h2; v2 -> h1; v2 -> h2; v3 -> h1; v3 -> h2; }')
            elif "reinforcement" in q:
                st.graphviz_chart('digraph { rankdir=LR; Agent -> Environment [label="Action"]; Environment -> Agent [label="Reward"]; }')
            else:
                st.graphviz_chart('digraph { Input -> Process -> Output; }')
                                    
