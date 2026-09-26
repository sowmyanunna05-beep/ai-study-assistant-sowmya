import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai

st.set_page_config(page_title="AI Study Assistant", page_icon="📚")
st.title("📚 AI Study Assistant")
st.caption("By Nunna Sowmya | 23B81A12D0")

api_key = st.secrets["Gemini_API_Key"]
pdf_file = st.file_uploader("PDF Upload Cheyu", type="pdf")

if pdf_file and api_key:
    genai.configure(api_key=api_key)
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"
    
    if len(text.strip()) < 50:
        st.error("Idi scanned image PDF! Text extract kaledu. Text unna vere PDF try cheyu (like IOT pdf)")
        st.info(f"Extracted characters: {len(text)}")
    else:
        st.success(f"PDF Ready! {len(text)} characters read!")
        
    question = st.text_input("Question Adugu:")
    
    if st.button("Answer Kavali") and question:
        with st.spinner("Answer ready chestunna..."):
            model = genai.GenerativeModel("gemini-3.8-flash")
            if len(text.strip()) < 50:
                prompt = f"Question: {question}. Answer in simple points."
            else:
                prompt = f"Answer from these notes: {text[:15000]} \n\n Question: {question} \n Give answer in 5 simple points."
            
            response = model.generate_content(prompt)
            st.write(response.text)
            
            
            if "diagram" in question.lower():
                st.subheader("📊 Diagram")
                st.graphviz_chart('''
                    digraph {
                        Input -> Encoder -> Code -> Decoder -> Output
                        Output -> Loss -> Backprop
                        Backprop -> Encoder
                        Backprop -> Decoder
                    }
                ''')
else:
    st.info("API Key + PDF pettu")
