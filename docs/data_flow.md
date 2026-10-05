# Data flow and lineage

How each source file moves through the layers, and what happens to it at each step.

```mermaid
flowchart TD
    subgraph RAW["raw (unchanged)"]
        R1["HOUSEHOLD.CSV<br/>177,656 rows"]
        R2["RTF1.CSV<br/>177,656 rows"]
        R3["MEMBER.CSV<br/>650,424 rows"]
        R4["RTF2.CSV<br/>610,590 rows"]
        R5["dictionary .xlsx<br/>value labels"]
        R6["psgc/regions.json<br/>17 regions"]
    end

    subgraph STG["staging (Parquet, one per source)"]
        S1[v1_household]
        S2[v1_household_questions]
        S3[v1_member]
        S4[v1_literacy]
        S5[codebook<br/>2,501 labels]
    end

    subgraph CUR["curated (Parquet + PostgreSQL)"]
        C0[dim_region]
        C1[household<br/>177,656]
        C2[member<br/>650,424]
        C3[literacy_assessment<br/>610,590]
        C4[agg_literacy_digital<br/>408]
        C5[person_profile<br/>650,424, partitioned by region]
    end

    R1 --> S1
    R2 --> S2
    R3 --> S3
    R4 --> S4
    R5 --> S5
    R6 --> C0
    S1 -->|"join on hhid (1:1)"| C1
    S2 -->|"join on hhid (1:1)"| C1
    S5 -.->|decode codes| C1
    S3 --> C2
    S5 -.->|decode codes| C2
    S4 --> C3
    S5 -.->|decode codes| C3
    C2 -->|"hhid (many:1)"| C5
    C1 --> C5
    C3 -->|"hhid + line_no (1:1)"| C5
    C0 --> C5
    C5 -->|"weighted rates, persons 10-64"| C4
```

## What each layer is allowed to do

| Layer | Allowed | Not allowed |
|---|---|---|
| **raw** | Store files exactly as downloaded / returned by the API; record checksum, size, rows, encoding, time (`data/raw/_manifests/`) | Any edit to the files |
| **staging** | Standardise column names (lower_snake_case, remove BOM); trim spaces; blank → missing; convert all-numeric columns to integer/decimal; remove exact duplicate rows and duplicate keys (rejected rows saved to `data/staging/_rejects/`); add lineage columns `source_file`, `source_line`, `batch_id`, `ingested_at`; parse the codebook | Joins, renaming to business names, derived fields |
| **curated** | Joins across sources; business names; decode codes with the PSA codebook; derived fields and business rules (below); weighted aggregates; partitioning | Changing source values other than by the documented rules |

## Transformation rules

| Rule | Where | Detail |
|---|---|---|
| Yes/no codes | `curated.yes_no` | PSA code 1 → `True`, 2 → `False`, anything else → missing |
| Unknown age | `curated.build_member` | Age 99 means "unknown" in the PSA codebook → missing (28 people) |
| Age groups | `config/pipeline.yaml` → `curated.age_groups` | 0-9, 10-14, 15-24, 25-34, 35-44, 45-54, 55-64, 65+ |
| Home internet | `curated.build_household` | Internet with cable **or** without cable |
| Digital access score | `curated.build_household` | smartphone + computer + tablet + home internet + mobile subscription (0-5) |
| Digital access tier | `config/pipeline.yaml` → `curated.digital_access_tiers` | 0 = No access, 1-2 = Low, 3 = Moderate, 4-5 = High |
| Region names | `curated.build_dim_region` | First two digits of the PSGC 10-digit code = PSA region code (05 Bicol, 17 MIMAROPA, 19 BARMM) |
| Region used for analysis | `curated.build_household` | `reg` (17 regions, matches PSGC). `reg2` (adds Negros Island Region, code 18) is kept as `region_code_nir` |
| Labels | `curated.code_labels` | Taken from the PSA data dictionary; leading codes such as "1 - " are removed |
| Weights | `curated.build_aggregate`, SQL queries | Literacy rates use `respondent_weight` (Form 2); household shares use `household_weight` |
| School attendance | `curated.build_member` | Codes 1-3 (public, private, home-schooled) → `True`; 4 → `False` |

## Tracing one record

Person `hhid = 1, line_no = 1`:

1. **raw** `MEMBER.CSV` line 2 (`HHID=000001, LNO=01`) and `RTF2.CSV` line 2 (`HHID=000001, LNO_F2= 1`)
2. **staging** `v1_member` row with `source_line = 2`; `v1_literacy` row with `source_line = 2` (codes now integers, so `01` and ` 1` both become `1`)
3. **curated** `member`, `literacy_assessment`, `household` rows with `hhid = 1`; `person_profile` partition `region_code=1`
4. **warehouse** `SELECT * FROM v_person_profile WHERE hhid = 1 AND line_no = 1;` (query 8 in `sql/02_representative_queries.sql`)
