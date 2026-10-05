"""Unit tests for the data-quality checks, using small hand-written tables."""
import pandas as pd

from src.validation import checks


def test_unique_flags_every_row_sharing_a_key():
    df = pd.DataFrame({"id": [1, 1, 2]})
    result = checks.check_unique(df, "t", ["id"])
    assert not result.passed and result.failing_rows == 2


def test_not_null():
    df = pd.DataFrame({"x": pd.array([1, None, 3], dtype="Int64")})
    assert checks.check_not_null(df, "t", "x").failing_rows == 1


def test_accepted_values_ignores_missing():
    df = pd.DataFrame({"sex": pd.array([1, 2, None, 3], dtype="Int64")})
    result = checks.check_accepted_values(df, "t", "sex", [1, 2])
    assert not result.passed and result.failing_rows == 1


def test_range():
    df = pd.DataFrame({"age": pd.array([0, 50, 130], dtype="Int64")})
    assert checks.check_range(df, "t", "age", 0, 120).failing_rows == 1


def test_foreign_key_finds_orphans():
    members = pd.DataFrame({"household_id": [1, 2, 9]})
    households = pd.DataFrame({"household_id": [1, 2]})
    result = checks.check_foreign_key(members, "member", ["household_id"],
                                      households, "household", ["household_id"])
    assert not result.passed and result.failing_rows == 1


def test_exact_duplicates_ignores_lineage_columns():
    df = pd.DataFrame({"a": [1, 1], "batch_id": ["x", "y"]})
    assert checks.check_exact_duplicates(df, "t", ignore=["batch_id"]).failing_rows == 1


def test_validate_table_runs_contract_rules():
    spec = {
        "min_rows": 2,
        "primary_key": ["id"],
        "columns": {"id": {"type": "integer", "nullable": False},
                    "age": {"type": "integer", "min": 0, "max": 120}},
    }
    df = pd.DataFrame({"id": pd.array([1, 2], dtype="Int64"), "age": pd.array([5, 200], dtype="Int64")})
    results = checks.validate_table(df, "t", spec, {})
    failed = [r.check for r in results if not r.passed]
    assert failed == ["range"]
