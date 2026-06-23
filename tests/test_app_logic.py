import math
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app_logic import load_glossary, translate_dataframe, translate_fallback, translate_term


# ---------------------------------------------------------------------------
# translate_term
# ---------------------------------------------------------------------------

class TestTranslateTerm:
    def test_found(self):
        glossary = {"Hello": "שלום", "World": "עולם"}
        assert translate_term("Hello", glossary) == "שלום"

    def test_not_found_returns_none(self):
        glossary = {"Hello": "שלום"}
        assert translate_term("Goodbye", glossary) is None

    def test_case_sensitive_miss(self):
        # Glossary keys are stored as-is; lowercase lookup must not match.
        glossary = {"Hello": "שלום"}
        assert translate_term("hello", glossary) is None

    def test_empty_string_key(self):
        glossary = {"Hello": "שלום"}
        assert translate_term("", glossary) is None

    def test_numeric_string_key(self):
        glossary = {"42": "ארבעים ושתיים"}
        assert translate_term("42", glossary) == "ארבעים ושתיים"

    def test_empty_glossary(self):
        assert translate_term("Hello", {}) is None


# ---------------------------------------------------------------------------
# load_glossary
# ---------------------------------------------------------------------------

class TestLoadGlossary:
    def test_basic_loading(self, tmp_path):
        df = pd.DataFrame({"English": ["Hello", "World"], "Hebrew": ["שלום", "עולם"]})
        path = tmp_path / "glossary.xlsx"
        df.to_excel(path, index=False)
        result = load_glossary(str(path))
        assert result == {"Hello": "שלום", "World": "עולם"}

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_glossary(str(tmp_path / "nonexistent.xlsx"))

    def test_missing_english_column_raises(self, tmp_path):
        df = pd.DataFrame({"Spanish": ["Hola"], "Hebrew": ["שלום"]})
        path = tmp_path / "glossary.xlsx"
        df.to_excel(path, index=False)
        with pytest.raises(KeyError):
            load_glossary(str(path))

    def test_missing_hebrew_column_raises(self, tmp_path):
        df = pd.DataFrame({"English": ["Hello"], "French": ["Bonjour"]})
        path = tmp_path / "glossary.xlsx"
        df.to_excel(path, index=False)
        with pytest.raises(KeyError):
            load_glossary(str(path))

    def test_duplicate_keys_last_value_wins(self, tmp_path):
        df = pd.DataFrame({"English": ["Hello", "Hello"], "Hebrew": ["שלום", "היי"]})
        path = tmp_path / "glossary.xlsx"
        df.to_excel(path, index=False)
        result = load_glossary(str(path))
        assert result["Hello"] == "היי"

    def test_whitespace_preserved_in_keys(self, tmp_path):
        # Keys with leading/trailing spaces are kept as-is, not stripped.
        df = pd.DataFrame({"English": [" Hello "], "Hebrew": ["שלום"]})
        path = tmp_path / "glossary.xlsx"
        df.to_excel(path, index=False)
        result = load_glossary(str(path))
        assert " Hello " in result
        assert "Hello" not in result


# ---------------------------------------------------------------------------
# translate_fallback
# ---------------------------------------------------------------------------

class TestTranslateFallback:
    def _make_client(self, content):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = content
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    def test_success_strips_whitespace(self):
        client = self._make_client("  שלום  ")
        assert translate_fallback("Hello", client) == "שלום"

    def test_passes_term_as_user_message(self):
        client = self._make_client("שלום")
        translate_fallback("Hello", client)
        call_kwargs = client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
        user_message = next(m for m in messages if m["role"] == "user")
        assert user_message["content"] == "Hello"

    def test_api_exception_returns_empty_string(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        assert translate_fallback("Hello", mock_client) == ""

    def test_whitespace_only_response_returns_empty_string(self):
        client = self._make_client("   ")
        assert translate_fallback("Hello", client) == ""

    def test_empty_response_returns_empty_string(self):
        client = self._make_client("")
        assert translate_fallback("Hello", client) == ""


# ---------------------------------------------------------------------------
# translate_dataframe
# ---------------------------------------------------------------------------

class TestTranslateDataframe:
    def _mock_client(self, translation):
        client = MagicMock()
        client.chat.completions.create.return_value.choices[
            0
        ].message.content = translation
        return client

    def test_glossary_match_replaced(self):
        glossary = {"Hello": "שלום"}
        df = pd.DataFrame({"A": ["Hello"]})
        result = translate_dataframe(df, glossary)
        assert result.at[0, "A"] == "שלום"

    def test_no_match_no_client_cell_unchanged(self):
        df = pd.DataFrame({"A": ["Unknown"]})
        result = translate_dataframe(df, {}, client=None)
        assert result.at[0, "A"] == "Unknown"

    def test_nan_cell_skipped(self):
        glossary = {"Hello": "שלום"}
        df = pd.DataFrame({"A": [float("nan")]})
        result = translate_dataframe(df, glossary)
        assert math.isnan(result.at[0, "A"])

    def test_fallback_applied_when_client_present(self):
        client = self._mock_client("שלום")
        df = pd.DataFrame({"A": ["Unknown"]})
        result = translate_dataframe(df, {}, client=client)
        assert result.at[0, "A"] == "**שלום**"

    def test_fallback_not_applied_when_no_client(self):
        df = pd.DataFrame({"A": ["Unknown"]})
        result = translate_dataframe(df, {}, client=None)
        assert result.at[0, "A"] == "Unknown"

    def test_multiple_columns_all_translated(self):
        glossary = {"Hello": "שלום", "World": "עולם"}
        df = pd.DataFrame({"A": ["Hello"], "B": ["World"]})
        result = translate_dataframe(df, glossary)
        assert result.at[0, "A"] == "שלום"
        assert result.at[0, "B"] == "עולם"

    def test_original_dataframe_not_mutated(self):
        glossary = {"Hello": "שלום"}
        df = pd.DataFrame({"A": ["Hello"]})
        translate_dataframe(df, glossary)
        assert df.at[0, "A"] == "Hello"

    def test_mixed_nan_and_values(self):
        glossary = {"Hello": "שלום"}
        df = pd.DataFrame({"A": [float("nan"), "Hello", float("nan")]})
        result = translate_dataframe(df, glossary)
        assert math.isnan(result.at[0, "A"])
        assert result.at[1, "A"] == "שלום"
        assert math.isnan(result.at[2, "A"])

    def test_glossary_match_takes_priority_over_fallback(self):
        glossary = {"Hello": "שלום"}
        client = self._mock_client("fallback-value")
        df = pd.DataFrame({"A": ["Hello"]})
        result = translate_dataframe(df, glossary, client=client)
        assert result.at[0, "A"] == "שלום"
        client.chat.completions.create.assert_not_called()

    def test_numeric_cells_converted_to_string_for_lookup(self):
        # Numeric cells are coerced via str() before lookup.
        glossary = {"42": "ארבעים ושתיים"}
        df = pd.DataFrame({"A": [42]})
        result = translate_dataframe(df, glossary)
        assert result.at[0, "A"] == "ארבעים ושתיים"
