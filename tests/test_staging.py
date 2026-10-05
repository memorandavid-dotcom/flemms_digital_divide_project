"""Unit tests for the staging helpers, using small hand-written tables."""
import pandas as pd

from src.transform.staging import clean_column_name, convert_types, deduplicate, standardise


def test_clean_column_name_removes_bom_and_spaces():
    assert clean_column_name("﻿FN") == "fn"
    assert clean_column_name(" Highest Grade (HGC) ") == "highest_grade_hgc"


def test_standardise_trims_and_marks_blanks_missing():
    df = pd.DataFrame({"REG": [" 1", "2 "], "Name": [" ", "x"]}, dtype="str")
    out = standardise(df)
    assert list(out.columns) == ["reg", "name"]
    assert out["reg"].tolist() == ["1", "2"]
    assert out["name"].isna().tolist() == [True, False]


def test_convert_types_only_converts_fully_numeric_columns():
    df = pd.DataFrame({"age": ["10", "20", None], "weight": ["1.5", "2", "3"], "code": ["01", "A2", "3"]},
                      dtype="str")
    out, converted = convert_types(df, keep_text=[])
    assert converted == {"age": "Int64", "weight": "Float64"}
    assert out["age"].tolist()[:2] == [10, 20]
    assert pd.api.types.is_string_dtype(out["code"])


def test_deduplicate_removes_exact_and_key_duplicates():
    df = pd.DataFrame({
        "hhid": [1, 1, 2, 2, 3],
        "lno": [1, 1, 1, 1, 1],
        "age": [30, 30, 40, 41, 50],  # row 2 is an exact copy; hhid 2 has a conflicting key
    })
    out, rejects, stats = deduplicate(df, key=["hhid", "lno"], data_columns=["hhid", "lno", "age"])
    assert stats["exact_duplicates_removed"] == 1
    assert stats["key_duplicates_removed"] == 1
    assert stats["rows_out"] == 3
    assert len(rejects) == 2  # both conflicting rows are kept for inspection
    assert not out.duplicated(subset=["hhid", "lno"]).any()
