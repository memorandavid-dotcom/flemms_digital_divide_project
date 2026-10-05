# Data dictionary (curated layer)

Tables in `data/curated/` (Parquet) and in the PostgreSQL warehouse. Types are PostgreSQL types; the Parquet files use the matching pandas types. Rules for every column are enforced by [data_contract.yaml](data_contract.yaml). Source codes and labels come from the PSA data dictionary shipped with the public-use file.

**Null?** = whether missing values are allowed.

## dim_region — 17 rows

| Column | Type | Null? | Description | Example / allowed values |
|---|---|---|---|---|
| region_code | smallint (PK) | No | PSA region code, first two digits of the PSGC code | 1, 13, 19 |
| region_name | text | No | Display name built from the PSGC API | "Region I - Ilocos Region", "National Capital Region" |
| region_short_name | text | No | Short PSGC name | "Ilocos Region", "NCR", "BARMM" |
| island_group | text | No | Island group | Luzon, Visayas, Mindanao |
| psgc_code | char(10) | No | 10-digit PSGC code | "0100000000" |

## household — 177,656 rows (one per surveyed household)

| Column | Type | Null? | Description | Example / allowed values |
|---|---|---|---|---|
| survey_year | smallint (PK) | No | FLEMMS round | 2024 |
| hhid | integer (PK) | No | Household ID (source `HHID`, unique nationwide) | 1 |
| region_code | smallint (FK → dim_region) | No | Region without Negros Island Region (source `REG`) | 1 |
| region_code_nir | smallint | No | Region with Negros Island Region, code 18 (source `REG2`) | 1, 18 |
| province_code | smallint | No | Province code (source `PRV`) | 28 |
| psu | integer | No | Primary sampling unit (source `PSU`) | 285 |
| urbanity | text | No | Urban/rural classification | Urban, Rural, No official classification |
| is_4ps_beneficiary | boolean | No | Household is a 4Ps (Pantawid) beneficiary (Q1) | true / false |
| has_electricity | boolean | No | Electricity in the house (Q12) | true / false |
| owns_smartphone | boolean | No | Owns a smartphone (Q13k) | true / false |
| owns_basic_phone | boolean | No | Owns a basic/keypad mobile phone (Q13j) | true / false |
| owns_computer | boolean | No | Owns a personal computer (Q13m) | true / false |
| owns_tablet | boolean | No | Owns a tablet (Q13l) | true / false |
| has_internet_cable | boolean | No | Internet with cable (Q14b) | true / false |
| has_internet_no_cable | boolean | No | Internet without cable, e.g. pocket Wi-Fi (Q14c) | true / false |
| has_home_internet | boolean | No | **Derived:** `has_internet_cable OR has_internet_no_cable` | true / false |
| has_mobile_subscription | boolean | No | Mobile subscription (Q14d) | true / false |
| used_ict_for_learning | boolean | No | Used ICT equipment for studying/learning in the past 12 months (Q22) | true / false |
| digital_access_score | smallint | No | **Derived:** count of smartphone, computer, tablet, home internet, mobile subscription | 0-5 |
| digital_access_tier | text | No | **Derived:** 0 = No access, 1-2 = Low, 3 = Moderate, 4-5 = High | No access, Low, Moderate, High |
| household_weight | numeric | No | Household final weight (source `RFACT` = `HH_RFACT`); use for household estimates | 96.239563 |
| batch_id | text | No | Pipeline run that loaded the row (lineage) | manual__2026-10-05T05:38:42… |

## member — 650,424 rows (one per household member)

| Column | Type | Null? | Description | Example / allowed values |
|---|---|---|---|---|
| survey_year | smallint (PK) | No | FLEMMS round | 2024 |
| hhid | integer (PK, FK → household) | No | Household ID | 1 |
| line_no | smallint (PK) | No | Line number in the household roster (source `LNO`) | 1-23 |
| sex | text | No | Sex (Q3) | Male, Female |
| age | smallint | Yes (28) | Age at last birthday (Q4); missing when PSA code 99 "unknown" | 0-98 |
| age_group | text | Yes (28) | **Derived** age band | 0-9, 10-14, 15-24, 25-34, 35-44, 45-54, 55-64, 65+ |
| relationship_code | smallint | No | Relationship to household head (Q5), PSA code | 1 = head |
| education_level_code | smallint | Yes | Highest grade completed, ISCED level (Q21, source `HGC_LEVEL`) | 0-8 |
| education_level | text | Yes | Label of the level from the PSA codebook | "Level 1 - Primary Education (Elementary)" |
| attending_school | boolean | Yes | Currently attending school (Q13): public, private or home-schooled → true | true / false; missing when not asked |
| member_weight | numeric | No | Member final weight (source `MEM_RFACT`); use for population estimates | 113.29949 |
| batch_id | text | No | Lineage | |

## literacy_assessment — 610,590 rows (one per person 5+ covered by Form 2)

| Column | Type | Null? | Description | Example / allowed values |
|---|---|---|---|---|
| survey_year | smallint (PK) | No | FLEMMS round | 2024 |
| hhid | integer (PK, FK → member) | No | Household ID | 1 |
| line_no | smallint (PK, FK → member) | No | Line number (source `LNO_F2`) | 1 |
| result_code | smallint | No | Form 2 interview result (PSA code) | 1-9 |
| result | text | No | Label of result_code | Completed Interview, Not at Home, Refused, Overseas, … |
| interview_completed | boolean | No | **Derived:** result_code = 1 | true / false |
| can_read | boolean | Yes | Reading indicator (10+ or 5-9 version) | true / false |
| can_write | boolean | Yes | Writing indicator (10+ or 5-9 version) | true / false |
| can_compute | boolean | Yes | Computation indicator (10+ or 5-9 version) | true / false |
| can_comprehend | boolean | Yes | Comprehension indicator (ages 10-64 only) | true / false |
| functional_literacy_level_code | smallint | Yes | Literacy level, ages 10-64 (source `FLLEVEL`) | 0-3 |
| functional_literacy_level | text | Yes | Label of the level | Illiterate, Low Literate, Basic Literate, Functional Literate |
| basic_literate | boolean | Yes | Basic literacy, ages 5+ (source `BLITERATE`) | true / false |
| functional_literate | boolean | Yes | **Functional literacy, ages 10-64** (source `FLITERATE`); missing outside 10-64 or if not interviewed | true / false |
| respondent_weight | numeric | No | Form 2 respondent weight (source `RESP_RFACT_F2`); 0 when not interviewed; **use for literacy rates** | 124.04051208 |
| batch_id | text | No | Lineage | |

## agg_literacy_digital — 408 rows

Persons 10-64 with a completed literacy assessment, grouped by region × age group × household digital access tier.

| Column | Type | Null? | Description | Example |
|---|---|---|---|---|
| survey_year | smallint (PK) | No | FLEMMS round | 2024 |
| region_code | smallint (PK, FK) | No | Region | 13 |
| age_group | text (PK) | No | Age band (10-14 … 55-64) | 15-24 |
| digital_access_tier | text (PK) | No | Household digital access tier | High |
| persons_sampled | integer | No | Unweighted number of persons in the cell | 3331 |
| weighted_population | numeric | No | Sum of respondent weights (estimated population) | 70254.15 |
| functional_literacy_rate | numeric | Yes | Weighted % functionally literate | 88.78 |
| basic_literacy_rate | numeric | Yes | Weighted % basic literate | 88.92 |
| batch_id | text | No | Lineage | |

Cells with few persons (see `persons_sampled`) give unstable rates; treat cells under about 100 persons with caution.

## person_profile (Parquet only) and v_person_profile (PostgreSQL view)

One row per member (650,424) with household, region and literacy columns joined, for analysis. Stored in `data/curated/person_profile/region_code=<n>/`. Columns: survey_year, hhid, line_no, sex, age, age_group, relationship_code, education_level_code, education_level, attending_school, member_weight, urbanity, has_electricity, owns_smartphone, owns_computer, owns_tablet, has_home_internet, has_mobile_subscription, used_ict_for_learning, digital_access_score, digital_access_tier, household_weight, interview_completed, basic_literate, functional_literate, functional_literacy_level, respondent_weight, region_name, region_code (the partition column).

The PostgreSQL view `v_person_profile` exposes the most-used subset of these columns (see `sql/01_create_schema.sql`).

## pipeline_run (PostgreSQL audit table)

| Column | Type | Description |
|---|---|---|
| run_id | bigserial (PK) | Load number |
| batch_id | text | Airflow run id or `cli_<timestamp>` |
| survey_year | smallint | Survey year loaded |
| started_at / finished_at | timestamptz | Load start and commit time |
| row_counts | jsonb | Rows loaded per table |
