-- FLEMMS 2024 digital divide warehouse schema (PostgreSQL 16).
-- Safe to run repeatedly: every object uses IF NOT EXISTS / OR REPLACE.
-- The pipeline runs this file automatically before each load (src/load/postgres_loader.py).

-- Lookup: regions with official PSGC names
CREATE TABLE IF NOT EXISTS dim_region (
    region_code        SMALLINT    PRIMARY KEY,
    region_name        TEXT        NOT NULL,
    region_short_name  TEXT        NOT NULL,
    island_group       TEXT        NOT NULL CHECK (island_group IN ('Luzon', 'Visayas', 'Mindanao')),
    psgc_code          CHAR(10)    NOT NULL UNIQUE
);

-- One row per surveyed household: location and digital access
CREATE TABLE IF NOT EXISTS household (
    survey_year              SMALLINT       NOT NULL,
    hhid                     INTEGER        NOT NULL,
    region_code              SMALLINT       NOT NULL REFERENCES dim_region (region_code),
    region_code_nir          SMALLINT       NOT NULL,
    province_code            SMALLINT       NOT NULL,
    psu                      INTEGER        NOT NULL,
    urbanity                 TEXT           NOT NULL,
    is_4ps_beneficiary       BOOLEAN        NOT NULL,
    has_electricity          BOOLEAN        NOT NULL,
    owns_smartphone          BOOLEAN        NOT NULL,
    owns_basic_phone         BOOLEAN        NOT NULL,
    owns_computer            BOOLEAN        NOT NULL,
    owns_tablet              BOOLEAN        NOT NULL,
    has_internet_cable       BOOLEAN        NOT NULL,
    has_internet_no_cable    BOOLEAN        NOT NULL,
    has_home_internet        BOOLEAN        NOT NULL,
    has_mobile_subscription  BOOLEAN        NOT NULL,
    used_ict_for_learning    BOOLEAN        NOT NULL,
    digital_access_score     SMALLINT       NOT NULL CHECK (digital_access_score BETWEEN 0 AND 5),
    digital_access_tier      TEXT           NOT NULL CHECK (digital_access_tier IN ('No access', 'Low', 'Moderate', 'High')),
    household_weight         NUMERIC(14, 8) NOT NULL CHECK (household_weight > 0),
    batch_id                 TEXT           NOT NULL,
    PRIMARY KEY (survey_year, hhid)
);
CREATE INDEX IF NOT EXISTS ix_household_region ON household (survey_year, region_code);

-- One row per household member
CREATE TABLE IF NOT EXISTS member (
    survey_year           SMALLINT       NOT NULL,
    hhid                  INTEGER        NOT NULL,
    line_no               SMALLINT       NOT NULL,
    sex                   TEXT           NOT NULL CHECK (sex IN ('Male', 'Female')),
    age                   SMALLINT       CHECK (age BETWEEN 0 AND 98),
    age_group             TEXT,
    relationship_code     SMALLINT,
    education_level_code  SMALLINT       CHECK (education_level_code BETWEEN 0 AND 8),
    education_level       TEXT,
    attending_school      BOOLEAN,
    member_weight         NUMERIC(14, 8) NOT NULL CHECK (member_weight > 0),
    batch_id              TEXT           NOT NULL,
    PRIMARY KEY (survey_year, hhid, line_no),
    FOREIGN KEY (survey_year, hhid) REFERENCES household (survey_year, hhid)
);

-- One row per person 5+ covered by the Form 2 literacy assessment
CREATE TABLE IF NOT EXISTS literacy_assessment (
    survey_year                     SMALLINT       NOT NULL,
    hhid                            INTEGER        NOT NULL,
    line_no                         SMALLINT       NOT NULL,
    result_code                     SMALLINT       NOT NULL,
    result                          TEXT           NOT NULL,
    interview_completed             BOOLEAN        NOT NULL,
    can_read                        BOOLEAN,
    can_write                       BOOLEAN,
    can_compute                     BOOLEAN,
    can_comprehend                  BOOLEAN,
    functional_literacy_level_code  SMALLINT       CHECK (functional_literacy_level_code BETWEEN 0 AND 3),
    functional_literacy_level       TEXT,
    basic_literate                  BOOLEAN,
    functional_literate             BOOLEAN,
    respondent_weight               NUMERIC(14, 8) NOT NULL CHECK (respondent_weight >= 0),
    batch_id                        TEXT           NOT NULL,
    PRIMARY KEY (survey_year, hhid, line_no),
    FOREIGN KEY (survey_year, hhid, line_no) REFERENCES member (survey_year, hhid, line_no)
);

-- Weighted literacy rates (persons 10-64) by region x age group x digital access tier
CREATE TABLE IF NOT EXISTS agg_literacy_digital (
    survey_year               SMALLINT      NOT NULL,
    region_code               SMALLINT      NOT NULL REFERENCES dim_region (region_code),
    age_group                 TEXT          NOT NULL,
    digital_access_tier       TEXT          NOT NULL,
    persons_sampled           INTEGER       NOT NULL CHECK (persons_sampled > 0),
    weighted_population       NUMERIC(16, 2) NOT NULL,
    functional_literacy_rate  NUMERIC(5, 2) CHECK (functional_literacy_rate BETWEEN 0 AND 100),
    basic_literacy_rate       NUMERIC(5, 2) CHECK (basic_literacy_rate BETWEEN 0 AND 100),
    batch_id                  TEXT          NOT NULL,
    PRIMARY KEY (survey_year, region_code, age_group, digital_access_tier)
);

-- Audit trail: one row per successful warehouse load
CREATE TABLE IF NOT EXISTS pipeline_run (
    run_id       BIGSERIAL    PRIMARY KEY,
    batch_id     TEXT         NOT NULL,
    survey_year  SMALLINT     NOT NULL,
    started_at   TIMESTAMPTZ  NOT NULL,
    finished_at  TIMESTAMPTZ  NOT NULL,
    row_counts   JSONB        NOT NULL
);

-- Analysis view: one row per person with household, region and literacy fields
CREATE OR REPLACE VIEW v_person_profile AS
SELECT m.survey_year,
       h.region_code,
       r.region_name,
       h.urbanity,
       m.hhid,
       m.line_no,
       m.sex,
       m.age,
       m.age_group,
       m.education_level,
       h.has_home_internet,
       h.owns_smartphone,
       h.owns_computer,
       h.digital_access_score,
       h.digital_access_tier,
       l.interview_completed,
       l.basic_literate,
       l.functional_literate,
       l.functional_literacy_level,
       l.respondent_weight
FROM member m
JOIN household h ON h.survey_year = m.survey_year AND h.hhid = m.hhid
JOIN dim_region r ON r.region_code = h.region_code
LEFT JOIN literacy_assessment l
       ON l.survey_year = m.survey_year AND l.hhid = m.hhid AND l.line_no = m.line_no;
