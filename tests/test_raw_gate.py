"""Unit tests for the raw gate, using small hand-written CSV files."""
from src.utils.io_utils import sha256_of
from src.validation.raw_gate import check_raw_file

RULES = {
    "min_rows": 3,
    "required_columns": ["HHID", "LNO_F2", "RESULT_CODE_F2", "RESP_RFACT_F2"],
    "key_columns": ["HHID", "LNO_F2"],
    "weight": {"column": "RESP_RFACT_F2", "positive_when": {"RESULT_CODE_F2": 1}},
}
GOOD = "HHID,LNO_F2,RESULT_CODE_F2,RESP_RFACT_F2\n1, 1,1,120.5\n1, 2,4,0\n2, 1,1,98.2\n"


def run(tmp_path, text, rules=RULES, manifest_entry=None):
    path = tmp_path / "rtf2.csv"
    path.write_text(text, encoding="utf-8")
    return {r.check: r for r in check_raw_file("v1_literacy", path, rules, manifest_entry)}


def test_good_file_passes_every_check(tmp_path):
    # Zero weight on a non-completed interview (result code 4) is allowed
    assert all(r.passed for r in run(tmp_path, GOOD).values())


def test_missing_column_fails_schema(tmp_path):
    text = "HHID,LNO_F2,RESP_RFACT_F2\n1,1,120.5\n1,2,0\n2,1,98.2\n"
    assert not run(tmp_path, text)["schema"].passed


def test_truncated_file_fails_row_count(tmp_path):
    assert not run(tmp_path, GOOD.rsplit("\n2,", 1)[0] + "\n")["row_count"].passed


def test_blank_key_fails(tmp_path):
    result = run(tmp_path, GOOD.replace("\n2, 1,", "\n2,,"))["key_not_blank"]
    assert not result.passed and result.failing_rows == 1


def test_completed_interview_needs_a_positive_weight(tmp_path):
    result = run(tmp_path, GOOD.replace("98.2", "0"))["weight"]
    assert not result.passed and result.failing_rows == 1


def test_unfinished_interview_must_have_zero_weight(tmp_path):
    assert not run(tmp_path, GOOD.replace(",4,0", ",4,55.0"))["weight"].passed


def test_file_changed_after_ingestion_fails_checksum(tmp_path):
    other = tmp_path / "other.csv"
    other.write_text(GOOD.replace("120.5", "121.0"), encoding="utf-8")
    assert not run(tmp_path, GOOD, manifest_entry={"sha256": sha256_of(other)})["checksum"].passed
