-- Short set of queries for the live demo (fits on one screen per step).
--   docker compose exec warehouse-db psql -U flemms -d flemms -f /sql/03_demo_queries.sql
-- The full set with explanations is in 02_representative_queries.sql.

\echo '=== 1. Rows loaded, and the load history (reruns never double the rows) ==='
SELECT (SELECT count(*) FROM household)           AS households,
       (SELECT count(*) FROM member)              AS members,
       (SELECT count(*) FROM literacy_assessment) AS literacy_records;

SELECT run_id, batch_id, finished_at::timestamp(0) AS finished, row_counts ->> 'member' AS member_rows
FROM pipeline_run ORDER BY run_id DESC LIMIT 3;

\echo '=== 2. Matches PSA published 2024 figures: 85.00M, 60.17M, 70.8%, 93.1% ==='
SELECT round(sum(respondent_weight) / 1e6, 2)                                    AS population_10_64_m,
       round(sum(respondent_weight) FILTER (WHERE functional_literate) / 1e6, 2) AS functionally_literate_m,
       round(100 * sum(respondent_weight) FILTER (WHERE functional_literate) / sum(respondent_weight), 1)
                                                                                 AS functional_literacy_pct,
       round(100 * sum(respondent_weight) FILTER (WHERE basic_literate)
             / sum(respondent_weight) FILTER (WHERE basic_literate IS NOT NULL), 1) AS basic_literacy_pct
FROM literacy_assessment
WHERE functional_literate IS NOT NULL;

\echo '=== 3. The answer: functional literacy rises with household digital access ==='
SELECT h.digital_access_tier,
       count(*) AS persons_sampled,
       round(100 * sum(l.respondent_weight) FILTER (WHERE l.functional_literate)
             / sum(l.respondent_weight), 1) AS functional_literacy_pct
FROM literacy_assessment l
JOIN household h USING (survey_year, hhid)
WHERE l.functional_literate IS NOT NULL
GROUP BY h.digital_access_tier
ORDER BY min(h.digital_access_score);

\echo '=== 4. Regional divide: highest and lowest home internet access ==='
(SELECT r.region_short_name AS region,
        round(100 * sum(h.household_weight) FILTER (WHERE h.has_home_internet) / sum(h.household_weight), 1)
            AS households_with_internet_pct
 FROM household h JOIN dim_region r USING (region_code)
 GROUP BY r.region_short_name ORDER BY 2 DESC LIMIT 3)
UNION ALL
(SELECT r.region_short_name,
        round(100 * sum(h.household_weight) FILTER (WHERE h.has_home_internet) / sum(h.household_weight), 1)
 FROM household h JOIN dim_region r USING (region_code)
 GROUP BY r.region_short_name ORDER BY 2 ASC LIMIT 3);

\echo '=== 5. Trace one person through the model (hhid 1, line 1) ==='
\x on
SELECT * FROM v_person_profile WHERE hhid = 1 AND line_no = 1;
\x off
