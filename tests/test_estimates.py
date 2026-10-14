"""Unit tests for the design-based estimates, on small hand-written samples."""
import pandas as pd
import pytest

from src.analysis.estimates import weighted_proportion


def test_simple_random_sample_gives_the_textbook_standard_error():
    # One stratum, one person per cluster, equal weights: SE = sqrt(p(1-p)/(n-1))
    df = pd.DataFrame({"y": [1, 1, 0, 0, 1], "w": 1.0, "stratum": 1, "psu": range(5)})
    row = weighted_proportion(df, "y", "w", "stratum", "psu").iloc[0]
    assert row["weighted_pct"] == pytest.approx(60.0)
    assert row["se_pct"] == pytest.approx(100 * (0.6 * 0.4 / 4) ** 0.5)
    assert row["unweighted_n"] == 5


def test_weights_and_groups():
    df = pd.DataFrame({"y": [1, 0, 1, 1], "w": [3.0, 1.0, 1.0, 1.0], "tier": ["A", "A", "B", "B"],
                       "stratum": 1, "psu": [1, 2, 3, 4]})
    rows = weighted_proportion(df, "y", "w", "stratum", "psu", by="tier").set_index("group")
    assert rows.loc["A", "weighted_pct"] == pytest.approx(75.0)  # 3 of 4 weighted people
    assert rows.loc["B", "weighted_pct"] == pytest.approx(100.0)
    assert rows.loc["A", "unweighted_n"] == 2


def test_clustering_widens_the_interval():
    # Same 0/1 values, but grouped into two clusters that differ completely
    independent = pd.DataFrame({"y": [1, 1, 0, 0], "w": 1.0, "stratum": 1, "psu": [1, 2, 3, 4]})
    clustered = independent.assign(psu=[1, 1, 2, 2])
    se_independent = weighted_proportion(independent, "y", "w", "stratum", "psu").iloc[0]["se_pct"]
    se_clustered = weighted_proportion(clustered, "y", "w", "stratum", "psu").iloc[0]["se_pct"]
    assert se_clustered > se_independent
