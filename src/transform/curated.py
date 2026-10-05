"""Staging -> curated: integrate the sources into analysis-ready tables.

Inputs (staging): v1_household, v1_household_questions, v1_member, v1_literacy,
codebook (PSA value labels) and the PSGC region list (raw JSON from the API).

Outputs (data/curated/, Parquet):
  dim_region            one row per region, official names from the PSGC API
  household             one row per household: location + digital access indicators
  member                one row per person: age group, sex, education
  literacy_assessment   one row per person tested (Form 2): literacy outcomes
  agg_literacy_digital  weighted functional-literacy rates by region x age group x access tier
  person_profile/       one row per person with everything joined, partitioned by region_code

Business rules (also in docs/data_dictionary.md):
  * yes/no survey codes: 1 = yes -> True, 2 = no -> False, anything else -> missing
  * age 99 means "unknown" in the PSA codebook -> missing
  * digital_access_score = smartphone + computer + tablet + home internet
    (cable or no cable) + mobile subscription, so 0 to 5
  * literacy rates are weighted with the Form 2 respondent weight (resp_rfact_f2),
    household shares with the household weight, as the PSA user's guide requires
"""
import re
import shutil

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds

from src.config import layer_path, settings
from src.utils.io_utils import read_json
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


# ---------- helpers ----------

def read_staging(name: str) -> pd.DataFrame:
    return pd.read_parquet(layer_path("staging") / f"{name}.parquet")


def code_labels(codebook: pd.DataFrame, variable: str) -> dict[int, str]:
    """Code -> label for one variable, e.g. {1: 'Male', 2: 'Female'}.

    PSA labels often start with the code ("1 - Male", "01 - Completed Interview");
    that prefix is removed.
    """
    rows = codebook[(codebook["variable"] == variable) & (codebook["value_from"] == codebook["value_to"])]
    return {int(r.value_from): re.sub(r"^\s*\d+\s*-?\s*", "", r.value_label).strip()
            for r in rows.itertuples() if r.value_label}


def yes_no(series: pd.Series) -> pd.Series:
    return series.map({1: True, 2: False}).astype("boolean")


def age_group(age: pd.Series) -> pd.Series:
    groups = settings()["curated"]["age_groups"]
    bounds = [g[0] for g in groups] + [200]
    labels = [g[1] for g in groups]
    return pd.cut(age, bins=bounds, labels=labels, right=False).astype("string")


def weighted_rate(flag: pd.Series, weight: pd.Series) -> float:
    """Weighted percentage of True values, ignoring missing flags."""
    known = flag.notna()
    if not known.any():
        return float("nan")
    return round(100 * float((flag[known].astype(int) * weight[known]).sum() / weight[known].sum()), 2)


# ---------- tables ----------

def build_dim_region() -> pd.DataFrame:
    regions = read_json(layer_path("raw") / settings()["sources"]["psgc_regions"]["folder"] / "regions.json")
    rows = []
    for r in regions:
        designation = r["regionName"]
        rows.append({
            # PSA numbers regions by the first two digits of the 10-digit PSGC code (05 = Bicol, 19 = BARMM)
            "region_code": int(r["psgc10DigitCode"][:2]),
            "region_name": f"{designation} - {r['name']}" if designation.startswith("Region ") else designation,
            "region_short_name": r["name"],
            "island_group": r["islandGroupCode"].title(),
            "psgc_code": r["psgc10DigitCode"],
        })
    return pd.DataFrame(rows).sort_values("region_code").reset_index(drop=True)


def build_household(year: int, batch_id: str, codebook: pd.DataFrame) -> pd.DataFrame:
    ids = read_staging("v1_household")
    q = read_staging("v1_household_questions")
    df = ids.merge(q.drop(columns=["reg", "reg2", "prv", "urbanity", "source_file", "source_line",
                                   "batch_id", "ingested_at", "hh_rfact"]),
                   on="hhid", how="inner", validate="one_to_one")
    if len(df) != len(ids):
        raise ValueError(f"household join lost rows: {len(ids):,} ids vs {len(df):,} joined")

    out = pd.DataFrame({
        "survey_year": year,
        "hhid": df["hhid"],
        "region_code": df["reg"],
        "region_code_nir": df["reg2"],
        "province_code": df["prv"],
        "psu": df["psu"],
        "urbanity": df["urbanity"].map(code_labels(codebook, "urbanity")).astype("string"),
        "is_4ps_beneficiary": yes_no(df["beneficiary_4ps"]),
        "has_electricity": yes_no(df["electricity"]),
        "owns_smartphone": yes_no(df["hh_smartphone"]),
        "owns_basic_phone": yes_no(df["hh_basicphone"]),
        "owns_computer": yes_no(df["hh_pc"]),
        "owns_tablet": yes_no(df["hh_tablet"]),
        "has_internet_cable": yes_no(df["hh_cabnet"]),
        "has_internet_no_cable": yes_no(df["hh_nocabnet"]),
        "has_mobile_subscription": yes_no(df["hh_mobsub"]),
        "used_ict_for_learning": yes_no(df["ict_equip"]),
        "household_weight": df["rfact"].astype("Float64"),
    })
    out.insert(out.columns.get_loc("has_mobile_subscription"), "has_home_internet",
               (out["has_internet_cable"] | out["has_internet_no_cable"]).astype("boolean"))
    score_parts = ["owns_smartphone", "owns_computer", "owns_tablet", "has_home_internet", "has_mobile_subscription"]
    out["digital_access_score"] = out[score_parts].astype("Int64").sum(axis=1, min_count=len(score_parts)).astype("Int64")
    tiers = {int(k): v for k, v in settings()["curated"]["digital_access_tiers"].items()}
    out["digital_access_tier"] = out["digital_access_score"].map(tiers).astype("string")
    out["batch_id"] = batch_id
    return out


def build_member(year: int, batch_id: str, codebook: pd.DataFrame) -> pd.DataFrame:
    m = read_staging("v1_member")
    age = m["age"].where(m["age"] != 99)  # 99 = unknown (PSA codebook)
    education = code_labels(codebook, "hgc_level")
    return pd.DataFrame({
        "survey_year": year,
        "hhid": m["hhid"],
        "line_no": m["lno"],
        "sex": m["sex"].map(code_labels(codebook, "sex")).astype("string"),
        "age": age.astype("Int64"),
        "age_group": age_group(age),
        "relationship_code": m["rel"],
        "education_level_code": m["hgc_level"],
        "education_level": m["hgc_level"].map(education).astype("string"),
        # 1-3 = attending (public / private / home-schooled), 4 = not attending
        "attending_school": m["attend_school"].map({1: True, 2: True, 3: True, 4: False}).astype("boolean"),
        "member_weight": m["mem_rfact"].astype("Float64"),
        "batch_id": batch_id,
    })


def build_literacy(year: int, batch_id: str, codebook: pd.DataFrame) -> pd.DataFrame:
    lit = read_staging("v1_literacy")
    # 5-9 year olds have their own reading/writing/computation indicators
    return pd.DataFrame({
        "survey_year": year,
        "hhid": lit["hhid"],
        "line_no": lit["lno_f2"],
        "result_code": lit["result_code_f2"],
        "result": lit["result_code_f2"].map(code_labels(codebook, "result_code_f2")).astype("string"),
        "interview_completed": (lit["result_code_f2"] == 1).astype("boolean"),
        "can_read": yes_no(lit["reading"].fillna(lit["reading59"])),
        "can_write": yes_no(lit["writing"].fillna(lit["writing59"])),
        "can_compute": yes_no(lit["compute"].fillna(lit["compute59"])),
        "can_comprehend": yes_no(lit["compre"]),
        "functional_literacy_level_code": lit["fllevel"],
        "functional_literacy_level": lit["fllevel"].map(code_labels(codebook, "fllevel")).astype("string"),
        "basic_literate": yes_no(lit["bliterate"]),
        "functional_literate": yes_no(lit["fliterate"]),
        "respondent_weight": lit["resp_rfact_f2"].astype("Float64"),
        "batch_id": batch_id,
    })


def build_person_profile(household, member, literacy, regions) -> pd.DataFrame:
    hh_cols = ["hhid", "region_code", "urbanity", "has_electricity", "owns_smartphone", "owns_computer",
               "owns_tablet", "has_home_internet", "has_mobile_subscription", "used_ict_for_learning",
               "digital_access_score", "digital_access_tier", "household_weight"]
    lit_cols = ["hhid", "line_no", "interview_completed", "basic_literate", "functional_literate",
                "functional_literacy_level", "respondent_weight"]
    df = (member.drop(columns="batch_id")
          .merge(household[hh_cols], on="hhid", how="left", validate="many_to_one")
          .merge(literacy[lit_cols], on=["hhid", "line_no"], how="left", validate="one_to_one")
          .merge(regions[["region_code", "region_name"]], on="region_code", how="left", validate="many_to_one"))
    if len(df) != len(member):
        raise ValueError(f"person_profile has {len(df):,} rows but member has {len(member):,}: join created duplicates")
    return df


def build_aggregate(profile: pd.DataFrame, year: int, batch_id: str) -> pd.DataFrame:
    """Weighted literacy rates for persons 10-64 with a completed literacy assessment."""
    assessed = profile[profile["functional_literate"].notna()]
    rows = []
    for (region, group, tier), g in assessed.groupby(["region_code", "age_group", "digital_access_tier"]):
        rows.append({
            "survey_year": year, "region_code": region, "age_group": group, "digital_access_tier": tier,
            "persons_sampled": len(g),
            "weighted_population": round(float(g["respondent_weight"].sum()), 2),
            "functional_literacy_rate": weighted_rate(g["functional_literate"], g["respondent_weight"]),
            "basic_literacy_rate": weighted_rate(g["basic_literate"], g["respondent_weight"]),
        })
    agg = pd.DataFrame(rows)
    agg["batch_id"] = batch_id
    return agg


def person_profile_dataset() -> ds.Dataset:
    """The partitioned person_profile folder as a pyarrow dataset.

    The partition column is declared as an integer; otherwise pyarrow would read
    the folder names (region_code=13) back as a category.
    """
    key = settings()["partitioning"]["column"]
    partitioning = ds.partitioning(pa.schema([(key, pa.int64())]), flavor="hive")
    return ds.dataset(layer_path("curated") / "person_profile", format="parquet", partitioning=partitioning)


def read_person_profile(region_code: int | None = None) -> pd.DataFrame:
    """Read all regions, or only one region's partition (partition pruning)."""
    key = settings()["partitioning"]["column"]
    dataset = person_profile_dataset()
    row_filter = (ds.field(key) == region_code) if region_code is not None else None
    df = dataset.to_table(filter=row_filter).to_pandas()
    df[key] = df[key].astype("Int64")
    return df


def build_curated(batch_id: str) -> dict:
    year = settings()["survey_year"]
    curated = layer_path("curated")
    codebook = read_staging("codebook")

    regions = build_dim_region()
    household = build_household(year, batch_id, codebook)
    member = build_member(year, batch_id, codebook)
    literacy = build_literacy(year, batch_id, codebook)
    profile = build_person_profile(household, member, literacy, regions)
    profile.insert(0, "survey_year", profile.pop("survey_year"))
    aggregate = build_aggregate(profile, year, batch_id)

    tables = {"dim_region": regions, "household": household, "member": member,
              "literacy_assessment": literacy, "agg_literacy_digital": aggregate}
    for name, df in tables.items():
        df.to_parquet(curated / f"{name}.parquet", index=False)
        log.info("Curated %-22s %9s rows x %d cols", name, f"{len(df):,}", len(df.columns))

    # Replace the whole partitioned dataset so reruns never leave stale partitions behind
    key = settings()["partitioning"]["column"]
    target = curated / "person_profile"
    shutil.rmtree(target, ignore_errors=True)
    profile.to_parquet(target, index=False, partition_cols=[key])
    log.info("Curated person_profile %9s rows, partitioned by %s into %d folders",
             f"{len(profile):,}", key, profile[key].nunique())

    # Small CSV copy of the aggregate for spreadsheet users
    aggregate.to_csv(layer_path("outputs") / "agg_literacy_digital.csv", index=False)
    return {name: len(df) for name, df in tables.items()} | {"person_profile": len(profile)}
