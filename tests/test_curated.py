"""Unit tests for the curated-layer business rules, using small hand-written tables."""
import pandas as pd

from src.transform.curated import age_group, code_labels, weighted_rate, yes_no


def test_yes_no_maps_survey_codes():
    out = yes_no(pd.Series([1, 2, 9, None], dtype="Int64"))
    assert out.tolist()[:2] == [True, False]
    assert out.isna().tolist()[2:] == [True, True]


def test_age_group_bands():
    ages = pd.Series([0, 9, 10, 24, 64, 65, 98, None], dtype="Int64")
    assert age_group(ages).tolist()[:7] == ["0-9", "0-9", "10-14", "15-24", "55-64", "65+", "65+"]


def test_code_labels_strip_leading_codes():
    codebook = pd.DataFrame({
        "variable": ["sex", "sex", "age"],
        "value_from": [1, 2, 0],
        "value_to": [1, 2, 98],  # ranges are not labels
        "value_label": ["1 - Male", "2 - Female", None],
    })
    assert code_labels(codebook, "sex") == {1: "Male", 2: "Female"}
    assert code_labels(codebook, "age") == {}


def test_weighted_rate_uses_weights_and_ignores_missing():
    flag = pd.Series([True, False, None], dtype="boolean")
    weight = pd.Series([3.0, 1.0, 100.0])
    assert weighted_rate(flag, weight) == 75.0
