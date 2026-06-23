import streamlit as st
import pandas as pd
from openai import OpenAI

from app_logic import load_glossary, translate_dataframe


@st.cache_data
def cached_load_glossary():
    return load_glossary()


glossary = cached_load_glossary()

openai_api_key = st.secrets.get("OPENAI_API_KEY", None)
if openai_api_key:
    client = OpenAI(api_key=openai_api_key)
else:
    client = None

st.title("Excel Translator")

uploaded_file = st.file_uploader("העלה קובץ Excel לתרגום", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    translated_df = translate_dataframe(df, glossary, client)

    st.dataframe(translated_df)
    st.download_button(
        label="📥 הורד קובץ מתורגם",
        data=translated_df.to_excel(index=False, engine='openpyxl'),
        file_name="translated.xlsx"
    )
