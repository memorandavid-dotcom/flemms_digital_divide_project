-- Representative queries for the FLEMMS 2024 warehouse.
-- Run inside the container (same command on Windows, macOS and Linux):
--   docker compose exec warehouse-db psql -U flemms -d flemms -f /sql/02_representative_queries.sql
-- Rates are survey-weighted: literacy uses respondent_weight, household shares use household_weight.

-- 1. Load check: row counts and the load history (rerun safety: counts stay the same)
SELECT (SELECT count(*) FROM household)            AS households,
       (SELECT count(*) FROM member)               AS members,
       (SELECT count(*) FROM literacy_assessment)  AS literacy_records,
       (SELECT count(*) FROM agg_literacy_digital) AS aggregate_rows;

SELECT run_id, batch_id, finished_at, row_counts ->> 'member' AS member_rows
FROM pipeline_run ORDER BY run_id DESC LIMIT 5;

-- 2. National functional literacy rate, persons 10-64
SELECT round(100 * sum(respondent_weight) FILTER (WHERE functional_literate)
             / sum(respondent_weight), 1) AS functional_literacy_rate_pct
FROM literacy_assessment
WHERE functional_literate IS NOT NULL;

-- 3. Functional literacy by household digital access tier
SELECT h.digital_access_tier,
       count(*) AS persons_sampled,
       round(100 * sum(l.respondent_weight) FILTER (WHERE l.functional_literate)
             / sum(l.respondent_weight), 1) AS functional_literacy_rate_pct
FROM literacy_assessment l
JOIN household h USING (survey_year, hhid)
WHERE l.functional_literate IS NOT NULL
GROUP BY h.digital_access_tier
ORDER BY min(h.digital_access_score);

-- 4. Digital divide by region: home internet access vs functional literacy
WITH access AS (
    SELECT region_code,
           round(100 * sum(household_weight) FILTER (WHERE has_home_internet) / sum(household_weight), 1)
               AS households_with_home_internet_pct
    FROM household GROUP BY region_code
), literacy AS (
    SELECT h.region_code,
           round(100 * sum(l.respondent_weight) FILTER (WHERE l.functional_literate)
                 / sum(l.respondent_weight), 1) AS functional_literacy_rate_pct
    FROM literacy_assessment l JOIN household h USING (survey_year, hhid)
    WHERE l.functional_literate IS NOT NULL
    GROUP BY h.region_code
)
SELECT r.region_name, a.households_with_home_internet_pct, lt.functional_literacy_rate_pct
FROM dim_region r
JOIN access a USING (region_code)
JOIN literacy lt USING (region_code)
ORDER BY a.households_with_home_internet_pct DESC;

-- 5. Digital divide by age group (persons 10-64)
SELECT m.age_group,
       round(100 * sum(l.respondent_weight) FILTER (WHERE h.has_home_internet) / sum(l.respondent_weight), 1)
           AS living_with_home_internet_pct,
       round(100 * sum(l.respondent_weight) FILTER (WHERE l.functional_literate) / sum(l.respondent_weight), 1)
           AS functional_literacy_rate_pct
FROM literacy_assessment l
JOIN member m USING (survey_year, hhid, line_no)
JOIN household h USING (survey_year, hhid)
WHERE l.functional_literate IS NOT NULL
GROUP BY m.age_group
ORDER BY m.age_group;

-- 6. Digital divide by education level (persons 10-64)
SELECT m.education_level,
       count(*) AS persons_sampled,
       round(100 * sum(l.respondent_weight) FILTER (WHERE h.digital_access_tier IN ('Moderate', 'High'))
             / sum(l.respondent_weight), 1) AS moderate_or_high_access_pct,
       round(100 * sum(l.respondent_weight) FILTER (WHERE l.functional_literate) / sum(l.respondent_weight), 1)
           AS functional_literacy_rate_pct
FROM literacy_assessment l
JOIN member m USING (survey_year, hhid, line_no)
JOIN household h USING (survey_year, hhid)
WHERE l.functional_literate IS NOT NULL
GROUP BY m.education_level_code, m.education_level
ORDER BY m.education_level_code NULLS FIRST;

-- 7. Urban vs rural
SELECT h.urbanity,
       round(100 * sum(l.respondent_weight) FILTER (WHERE h.has_home_internet) / sum(l.respondent_weight), 1)
           AS living_with_home_internet_pct,
       round(100 * sum(l.respondent_weight) FILTER (WHERE l.functional_literate) / sum(l.respondent_weight), 1)
           AS functional_literacy_rate_pct
FROM literacy_assessment l
JOIN household h USING (survey_year, hhid)
WHERE l.functional_literate IS NOT NULL
GROUP BY h.urbanity;

-- 8. Trace one person through the model (live demo: pick any hhid / line_no)
SELECT * FROM v_person_profile WHERE hhid = 1 AND line_no = 1;

-- 9. Ready-made aggregate for dashboards: NCR, by age group and access tier
SELECT a.age_group, a.digital_access_tier, a.persons_sampled, a.functional_literacy_rate
FROM agg_literacy_digital a
WHERE a.region_code = 13
ORDER BY a.age_group, a.digital_access_tier;
