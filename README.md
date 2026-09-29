# FLEMMS 2024 Digital Divide & Functional Literacy Project

## Project Overview
This Data Engineering and Analytics project analyzes the **2024 Functional Literacy, Education, and Mass Media Survey (FLEMMS)** dataset from the Philippine Statistics Authority (PSA), covering 172,800 households. 

**Problem Statement:** Is there a digital divide between different age groups, geographic regions, and educational levels in the Philippines, and to what extent does this digital divide relate to the functional literacy of the population?

## Project Status: ETL Pipeline & Analytical Base Table Established
We have successfully established a robust ETL (Extract, Transform, Load) pipeline, culminating in a ready-for-analysis Analytical Base Table (ABT). Due to the massive size of the raw data (surpassing GitHub's 100MB limit), the pipeline is designed to run locally or in cloud environments (like Google Colab) while keeping version control strictly to the source code.

### Key Accomplishments
1. **Data Ingestion & Partitioning:** Successfully extracted multi-year raw CSV files, handled legacy encoding (`latin-1`), and partitioned massive datasets into `/households` and `/individuals` directories to optimize memory.
2. **Data Cleaning & Schema Harmonization:** Automated the standardization of column schemas to `lower_snake_case`, handled tokenization errors, eliminated exact duplicates, and dropped fully empty columns.
3. **Modular ETL Architecture:** Built reusable Python scripts (`src/extract.py`, `src/transform.py`, `src/load.py`) to systematically merge household digital access data with individual demographic data using geographic and household keys.
4. **Optimized Final Storage:** Exported the merged data as a compressed Apache Parquet file (`flemms_analytical_base_table.parquet`), significantly reducing read times and preparing the data for the Data Scientist.
5. **Feature Engineering & Visualization Framework:** Laid the groundwork for calculating a `digital_access_score` and `literacy_tier`, along with basic Matplotlib/Seaborn visualization scripts for exploratory stakeholder reporting.

## Folder Structure
```text
flemms_digital_divide_project/
│
├── data/
│   ├── raw/          # Untouched raw survey files & metadata (Ignored in Git)
│   ├── processed/    # Partitioned household and individual CSVs (Ignored)
│   └── final/        # Clean Parquet analytical base tables (Ignored)
│
├── notebooks/        # Jupyter notebooks for EDA and ETL prototyping
├── sql/              # schema.sql documenting final table architecture
├── src/              # Modular ETL Python scripts
│   ├── __init__.py
│   ├── extract.py
│   ├── transform.py
│   └── load.py
│
├── pipeline.py       # Main pipeline orchestrator
├── requirements.txt  # Project dependencies (pandas, pyarrow, etc.)
└── .gitignore        # Blocks large data files from exceeding GitHub size limits