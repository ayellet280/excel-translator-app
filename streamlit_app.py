import streamlit as st
import pandas as pd
from openai import OpenAI
import openai
import os

# קריאת קובץ מילון מונחים
@st.cache_data
def load_glossary():
    glossary = pd.read_excel("glossary.xlsx")
    glossary_dict = dict(zip(glossary['English'], glossary['Hebrew']))
    return glossary_dict

# תרגום מונחים באמצעות מילון
def translate_term(term, glossary):
    return glossary.get(term)

# תרגום מונחים שלא קיימים במילון באמצעות OpenAI
def translate_fallback(term, client):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional translator. Translate the word to Hebrew."},
                {"role": "user", "content": term}
            ]
        )
        return response.choices[0].message.content.strip()
    except:
        return ""

# טעינת מילון מונחים
glossary = load_glossary()

# הגדרת מפתח OpenAI
openai_api_key = st.secrets.get("OPENAI_API_KEY", None)
if openai_api_key:
    client = OpenAI(api_key=openai_api_key)
else:
    client = None

st.title("Excel Translator")

uploaded_file = st.file_uploader("העלה קובץ Excel לתרגום", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    translated_df = df.copy()

    for col in df.columns:
        for i, cell in enumerate(df[col]):
            if pd.isna(cell):
                continue
            translation = translate_term(str(cell), glossary)
            if translation:
                translated_df.at[i, col] = translation
            elif client:
                fallback_translation = translate_fallback(str(cell), client)
                translated_df.at[i, col] = f"**{fallback_translation}**"  # מודגש
                # כאן סימון רק ב-DataFrame viewer, לא בקובץ המורד
            else:
                translated_df.at[i, col] = cell  # השאר כמו שהוא

    st.dataframe(translated_df)
    st.download_button(
        label="📥 הורד קובץ מתורגם",
        data=translated_df.to_excel(index=False, engine='openpyxl'),
        file_name="translated.xlsx"
    )