import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai

st.set_page_config(page_title="AI Study Assistant", page_icon="📚")
st.title("📚 AI Study Assistant")
st.caption("By Nunna Sowmya | 23B81A12D0")

api_key = st.secrets["GEMINI_API_KEY"]
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
        st.error("Idi scanned image PDF! Text extract kaledu.")
    else:
        st.success(f"PDF Ready! {len(text)} characters")
        st.info(f"Extracted characters: {len(text)}")

        question = st.text_input("Question Adugu (diagram kavali ante diagram ani rayi)")

        if st.button("Answer Kavali"):
            if question.strip() == "":
                st.warning("Question rayi Sowmya!")
            else:
                with st.spinner("Answer ready chestunna..."):
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    prompt = f"Answer in simple Telugu + English mix in 5 points. PDF: {text[:12000]} Question: {question}"
                    response = model.generate_content(prompt)
                    st.write(response.text)

                    # --- DIAGRAM RAVADANIKI PROCESS ---
                    if "diagram" in question.lower():
                        st.subheader("📊 Topic Related Diagram")

                        if "reinforcement" in question.lower() or "reinforcement" in text.lower()[:2000]:
                            st.graphviz_chart('''
                                digraph {
                                    rankdir=LR;
                                    Agent [shape=box, style=filled, fillcolor=lightblue];
                                    Environment [shape=box, style=filled, fillcolor=lightgreen];
                                    Agent -> Environment [label=" Action "];
                                    Environment -> Agent [label=" State + Reward "];
                                }
                            ''')
                        elif "autoencoder" in question.lower():
                            st.graphviz_chart('''
                                digraph {
                                    rankdir=LR;
                                    Input [shape=box];
                                    Encoder [shape=box, style=filled, fillcolor=orange];
                                    Code [label="Code\\nBottleneck", shape=circle, style=filled, fillcolor=yellow];
                                    Decoder [shape=box, style=filled, fillcolor=orange];
                                    Output [shape=box];
                                    Input -> Encoder -> Code -> Decoder -> Output;
                                }
                            ''')
                        else:
                            st.graphviz_chart('''
                                digraph {
                                    Input -> Processing -> Output;
                                }
                            ''')
                        st.caption("Idi PDF lo unna topic batti vachina diagram. PDF photo same to same kadu, kani topic ki correct diagram ye!")
