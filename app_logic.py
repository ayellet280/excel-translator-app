import pandas as pd


def load_glossary(path="glossary.xlsx"):
    glossary = pd.read_excel(path)
    glossary_dict = dict(zip(glossary['English'], glossary['Hebrew']))
    return glossary_dict


def translate_term(term, glossary):
    return glossary.get(term)


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
    except Exception:
        return ""


def translate_dataframe(df, glossary, client=None):
    # Cast to object so string translations can be written into any typed column.
    translated_df = df.copy().astype(object)
    for col in df.columns:
        for i, cell in enumerate(df[col]):
            if pd.isna(cell):
                continue
            translation = translate_term(str(cell), glossary)
            if translation:
                translated_df.at[i, col] = translation
            elif client:
                fallback_translation = translate_fallback(str(cell), client)
                translated_df.at[i, col] = f"**{fallback_translation}**"
            else:
                translated_df.at[i, col] = cell
    return translated_df
