# Live demo runbook

Everything needed to run the live demonstration: one-time laptop setup, the checks to do before presenting, the demo itself (about 7 minutes) and a backup plan. All commands are for **PowerShell**, run from the repository folder.

---

## Part A: Set up the demo laptop (do this the night before, with good internet)

| # | Step | Command / action | Done when |
|---|---|---|---|
| A1 | Install **Docker Desktop** (needs Windows 10/11 with WSL 2; may ask for a restart) | <https://www.docker.com/products/docker-desktop/> | Docker Desktop opens and shows "Engine running" |
| A2 | Give Docker enough memory | Laptop with 8 GB RAM: close other apps during the demo. 16 GB is comfortable | — |
| A3 | Get the code | `git clone https://github.com/memorandavid-dotcom/flemms_digital_divide_project.git` then `cd flemms_digital_divide_project` | Folder exists |
| A4 | Put the survey files in place | Copy the 4 CSVs and `flemms_2024_v1_metadata(dictionary).xlsx` into `data\raw\PHL-PSA-FLEMMS-2024-V1-PUF\` | `dir data\raw\PHL-PSA-FLEMMS-2024-V1-PUF` lists 5 files |
| A5 | Create the configuration | `Copy-Item .env.example .env` then `notepad .env` and replace every `change_me` with a password of your choice | `.env` saved |
| A6 | Build and start (downloads about 1.5 GB the first time) | `docker compose up -d --build` | Command finishes |
| A7 | Check health (wait 1-2 minutes) | `docker compose ps` | airflow-apiserver, airflow-scheduler, airflow-dag-processor, airflow-db, warehouse-db all show `healthy` |
| A8 | Log in to Airflow | Open <http://localhost:8080>, user/password = `_AIRFLOW_WWW_USER_USERNAME` / `_AIRFLOW_WWW_USER_PASSWORD` from `.env` | DAG `flemms_digital_divide_pipeline` is listed |
| A9 | **Full successful run** | In Airflow: switch the DAG on, press **Trigger**. Takes about 5-7 minutes | All 9 tasks green |
| A10 | **Create a failed run to show tomorrow** | Rename `data\raw\PHL-PSA-FLEMMS-2024-V1-PUF\FLEMMS PUF 2024 Volume1 - RTF2.CSV` to `RTF2.CSV.bak`, trigger the DAG, wait until `ingest_survey_files` turns red (about 4 minutes: it retries twice), then **rename the file back** | One red run in the history |
| A11 | Second successful run (shows reruns don't duplicate) | Trigger again | Green; `pipeline_run` has 2 rows with the same member count |
| A12 | Test the demo queries | `docker compose exec warehouse-db psql -U flemms -d flemms -f /sql/03_demo_queries.sql` | 5 result blocks; 70.8 appears in block 2 |
| A13 | Rehearse Part C once, with a timer | — | Under 8 minutes |
| A14 | Record a backup | Take screenshots of the green run, a task log and the query results (or a short screen recording with **Win + Alt + R**) | Files saved |

If you changed `WAREHOUSE_USER` or `WAREHOUSE_DB` in `.env`, use those instead of `flemms` in the psql commands.

---

## Part B: Before presenting (15 minutes before)

1. Start **Docker Desktop** and wait for "Engine running".
2. In PowerShell, in the repo folder: `docker compose up -d`, then `docker compose ps` until everything is `healthy`.
3. Open and arrange:
   - Browser tab 1: <http://localhost:8080>, logged in, on the DAG page
   - Browser tab 2: the GitHub repository (README)
   - VS Code with the repo open (Explorer showing `data\curated\person_profile\` and `outputs\`)
   - PowerShell in the repo folder, font size enlarged (Ctrl + mouse wheel)
4. Phone hotspot ready in case venue Wi-Fi fails. Only the region API needs internet, and the pipeline falls back to the saved copy if it is offline.
5. Close Teams/Discord/notifications.

---

## Part C: The demo (about 7 minutes)

| Time | Show | Say (in your own words) |
|---|---|---|
| 0:00 | **Airflow → DAG → Graph** | "This is our pipeline in Airflow: 9 tasks. Ingestion of the PSA survey files and the PSGC region API, then staging, validation, curation, validation again, and loading into PostgreSQL. It is scheduled monthly, every task retries twice, and data-quality failures stop the pipeline immediately." |
| 0:45 | Press **Trigger** (in the dialog you can untick `run_format_benchmark` to save a minute) | "We'll start a fresh run now and come back to it at the end." |
| 1:00 | **VS Code**: `data\raw`, `data\staging`, `data\curated\person_profile\region_code=13\` | "Raw files are never modified. Staging is cleaned, typed, de-duplicated Parquet. Curated is joined and analysis-ready; the person table is partitioned by region, so reading NCR touches 1 of 17 folders." |
| 2:00 | **Airflow**: click the running `ingest_survey_files` or a finished `validate_staging` square → **Logs** | "Every step logs what it did: file checksums and row counts, and here each of the 117 checks with PASS. Row reconciliation proves no row was lost: raw rows equal staged rows plus removed duplicates." |
| 3:00 | **Airflow**: open last night's **red run** → red `ingest_survey_files` → **Logs** | "This is how we diagnose failures. We removed one source file. The task tried 3 times, then failed with a clear message naming the missing file, and the downstream tasks did not run, so no bad data reached the database." |
| 4:00 | **PowerShell**: `docker compose exec warehouse-db psql -U flemms -d flemms -f /sql/03_demo_queries.sql` | Walk through the 5 blocks (below) |
| 4:00 | Block 1 | "1.4 million rows loaded. The load history shows several runs, and the member count is always 650,424: rerunning never duplicates data, because each load replaces that survey year in one transaction." |
| 4:30 | Block 2 | "Our weighted results match PSA's official 2024 press release exactly: 85.00 million people aged 10-64, 70.8% functionally literate, 93.1% basic literacy. That proves our joins and survey weights are correct." |
| 5:00 | Block 3 | "This answers our question: functional literacy rises from 53.6% in households with no digital access to 83.0% with high access. This is an association, not proof of cause." |
| 5:30 | Block 4 | "Home internet ranges from 53% of households in NCR to 6% in BARMM." |
| 6:00 | Block 5 | "And we can trace any person from the raw file through every table, here household 1, person 1." |
| 6:30 | **Airflow**: the new run | "The run we started is now green (or almost done). If we rerun the load query, the row counts stay the same." |

If the run is still going at 6:30, say so and show the tasks already green; it finishes in about 5-7 minutes.

---

## Part D: Backup plan

| Problem | What to do |
|---|---|
| Docker Desktop will not start | Restart Docker Desktop once. If that fails, switch to the second laptop that was set up (Jenna's) |
| `docker compose ps` shows `starting` for a long time | Wait 2 minutes; Airflow takes a while after a cold start |
| Airflow page does not load | `docker compose restart airflow-apiserver`, wait 1 minute |
| A task fails live | That's fine to show: open the log, read the error, explain retries/fail-fast, then continue with the database queries (the data from last night's run is still there) |
| Nothing works | Use the screenshots / recording from step A14, and say clearly that they are from the run made the night before |

---

## Useful extra commands

```powershell
docker compose run --rm pipeline-cli python pipeline.py --list            # stage names
docker compose run --rm pipeline-cli pytest                               # 15 unit tests
docker compose exec warehouse-db psql -U flemms -d flemms                 # interactive SQL (\q to quit)
docker compose down                                                       # stop everything after the presentation
```
