"""Key estimates with design-based uncertainty (outputs/analysis/key_estimates.csv).

FLEMMS is a clustered, weighted sample, so a weighted rate alone looks more precise
than it is. For every headline comparison this module reports the unweighted sample
size, the weighted rate, its standard error, a 95% confidence interval and the
design effect (how much the survey design widens the interval compared with a
simple random sample of the same size).

Method: Taylor linearization of the weighted ratio (the standard approach for
complex surveys), treating each sampled PSU as a cluster. The public-use file has
PSU numbers but no stratum variable, so regions are used as strata and a cluster is
identified by (region, province, PSU). Grouping PSUs into these broad strata tends to
overstate the variance slightly, so the intervals are, if anything, a little too wide.
"""
import numpy as np
import pandas as pd

from src.config import layer_path
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

Z_95 = 1.96
TIER_ORDER = ["No access", "Low", "Moderate", "High"]


def weighted_proportion(df: pd.DataFrame, y: str, w: str, strata: str, cluster: str,
                        by: str | None = None) -> pd.DataFrame:
    """Weighted share of y (0/1) overall or per group of `by`, with a linearized standard error."""
    groups = [None] if by is None else list(df[by].dropna().unique())
    weight, value = df[w].to_numpy(dtype=float), df[y].to_numpy(dtype=float)
    strata_id, cluster_id = df[strata].to_numpy(), df[cluster].to_numpy()
    n_clusters = pd.Series(cluster_id).groupby(strata_id).nunique()
    rows = []
    for group in groups:
        in_group = (np.ones(len(df), dtype=bool) if group is None
                    else (df[by] == group).fillna(False).to_numpy(dtype=bool))
        weights = weight * in_group
        total = weights.sum()
        p = (weights * value).sum() / total
        # Linearized value of each person, summed per cluster; clusters with nobody
        # in the group still count, with a total of 0
        z = pd.Series(weights * (value - p) / total).groupby([strata_id, cluster_id]).sum()
        deviations = z - z.groupby(level=0).transform("mean")
        n_h = n_clusters.reindex(z.index.get_level_values(0)).to_numpy()
        variance = float(((n_h / (n_h - 1)) * deviations.to_numpy() ** 2)[n_h > 1].sum())
        se = variance ** 0.5
        n = int(in_group.sum())  # unweighted sample size
        srs_variance = p * (1 - p) / n
        rows.append({"group": "All" if group is None else group, "unweighted_n": n,
                     "weighted_pct": 100 * p, "se_pct": 100 * se,
                     "ci95_low": 100 * max(p - Z_95 * se, 0.0), "ci95_high": 100 * min(p + Z_95 * se, 1.0),
                     "design_effect": variance / srs_variance if srs_variance > 0 else float("nan")})
    return pd.DataFrame(rows)


def estimate_key_indicators(batch_id: str) -> dict:
    """Estimate the headline rates with 95% confidence intervals and save them as CSV."""
    curated = layer_path("curated")
    household = pd.read_parquet(curated / "household.parquet")
    household["cluster"] = (household["region_code"].astype(str) + "-" + household["province_code"].astype(str)
                            + "-" + household["psu"].astype(str))
    regions = pd.read_parquet(curated / "dim_region.parquet").set_index("region_code")["region_short_name"]

    literacy = pd.read_parquet(curated / "literacy_assessment.parquet")
    persons = literacy[literacy["functional_literate"].notna()].merge(
        household[["survey_year", "hhid", "region_code", "cluster", "digital_access_tier"]],
        on=["survey_year", "hhid"], how="left", validate="many_to_one")
    persons["functional"] = persons["functional_literate"].astype(float)
    persons["basic"] = persons["basic_literate"].astype(float)
    household["internet"] = household["has_home_internet"].astype(float)

    design = {"strata": "region_code", "cluster": "cluster"}
    parts = [
        ("Functional literacy (persons 10-64)", "National",
         weighted_proportion(persons, "functional", "respondent_weight", **design)),
        ("Basic literacy (persons 10-64)", "National",
         weighted_proportion(persons[persons["basic"].notna()], "basic", "respondent_weight", **design)),
        ("Functional literacy (persons 10-64)", "Digital access tier",
         weighted_proportion(persons, "functional", "respondent_weight", by="digital_access_tier", **design)),
        ("Functional literacy (persons 10-64)", "Region",
         weighted_proportion(persons, "functional", "respondent_weight", by="region_code", **design)),
        ("Households with home internet", "National",
         weighted_proportion(household, "internet", "household_weight", **design)),
        ("Households with home internet", "Region",
         weighted_proportion(household, "internet", "household_weight", by="region_code", **design)),
    ]
    frames = []
    for indicator, breakdown, frame in parts:
        frame.insert(0, "breakdown", breakdown)
        frame.insert(0, "indicator", indicator)
        if breakdown == "Region":
            frame["group"] = frame["group"].map(regions)
            frame = frame.sort_values("weighted_pct", ascending=False)
        elif breakdown == "Digital access tier":
            frame = frame.set_index("group").reindex(TIER_ORDER).reset_index()
        frames.append(frame)

    table = pd.concat(frames, ignore_index=True)
    for column in ["weighted_pct", "se_pct", "ci95_low", "ci95_high"]:
        table[column] = table[column].round(2)
    table["design_effect"] = table["design_effect"].round(2)
    table["batch_id"] = batch_id

    out_dir = layer_path("outputs") / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "key_estimates.csv"
    table.to_csv(out, index=False)

    for _, r in table[table["breakdown"] != "Region"].iterrows():
        log.info("%s | %s: %.1f%% (95%% CI %.1f-%.1f, n=%s, deff %.1f)", r["indicator"], r["group"],
                 r["weighted_pct"], r["ci95_low"], r["ci95_high"], f"{r['unweighted_n']:,}", r["design_effect"])
    log.info("Saved %d estimates to %s", len(table), out)
    return {"estimates": len(table), "file": str(out)}
