# Warehouse ERD (PostgreSQL)

Created by `sql/01_create_schema.sql`. Keys: **PK** primary key, **FK** foreign key. Image file: [images/erd.png](images/erd.png).

```mermaid
erDiagram
    direction LR
    dim_region ||--o{ household : "region_code"
    dim_region ||--o{ agg_literacy_digital : "region_code"
    household ||--|{ member : "survey_year, hhid"
    member ||--o| literacy_assessment : "survey_year, hhid, line_no"

    dim_region {
        smallint region_code PK
        text region_name
        text region_short_name
        text island_group
        char psgc_code UK
    }
    household {
        smallint survey_year PK
        integer hhid PK
        smallint region_code FK
        smallint region_code_nir
        smallint province_code
        integer psu
        text urbanity
        boolean has_electricity
        boolean owns_smartphone
        boolean owns_computer
        boolean owns_tablet
        boolean has_home_internet
        boolean has_mobile_subscription
        boolean used_ict_for_learning
        smallint digital_access_score
        text digital_access_tier
        numeric household_weight
        text batch_id
    }
    member {
        smallint survey_year PK, FK
        integer hhid PK, FK
        smallint line_no PK
        text sex
        smallint age
        text age_group
        smallint education_level_code
        text education_level
        boolean attending_school
        numeric member_weight
        text batch_id
    }
    literacy_assessment {
        smallint survey_year PK, FK
        integer hhid PK, FK
        smallint line_no PK, FK
        smallint result_code
        boolean interview_completed
        boolean can_read
        boolean can_write
        boolean can_compute
        boolean can_comprehend
        smallint functional_literacy_level_code
        boolean basic_literate
        boolean functional_literate
        numeric respondent_weight
        text batch_id
    }
    agg_literacy_digital {
        smallint survey_year PK
        smallint region_code PK, FK
        text age_group PK
        text digital_access_tier PK
        integer persons_sampled
        numeric weighted_population
        numeric functional_literacy_rate
        numeric basic_literacy_rate
        text batch_id
    }
    pipeline_run {
        bigserial run_id PK
        text batch_id
        smallint survey_year
        timestamptz started_at
        timestamptz finished_at
        jsonb row_counts
    }
```

Not every column is drawn (e.g. `owns_basic_phone`, `has_internet_cable`, `result`); the full list is in [data_dictionary.md](data_dictionary.md).

## Relationships

| From | To | Cardinality | Meaning |
|---|---|---|---|
| `household.region_code` | `dim_region.region_code` | many → one | Each household is in one region |
| `member (survey_year, hhid)` | `household` | many → one | Each person belongs to one household; every household has at least one member |
| `literacy_assessment (survey_year, hhid, line_no)` | `member` | one → one (optional) | Persons 5+ covered by Form 2 have one assessment row; younger children have none |
| `agg_literacy_digital.region_code` | `dim_region` | many → one | Aggregates are per region |

`pipeline_run` is an audit table with no foreign keys. The view `v_person_profile` joins member, household, dim_region and literacy_assessment.

## Why this design

- **Natural composite keys** (`survey_year, hhid, line_no`) come straight from the survey, so a record can be traced back to the source file without a lookup table. `survey_year` is part of every key so a future FLEMMS round can be loaded next to 2024.
- **Normalised tables + one view** instead of one wide table: household attributes are stored once (177,656 rows) instead of repeated for every member (650,424 rows).
- **Constraints mirror the data contract** (`CHECK` on ages, scores, rates, tiers; `NOT NULL` where the contract says `nullable: false`), so bad data is rejected even if someone loads it without the Python validation.
