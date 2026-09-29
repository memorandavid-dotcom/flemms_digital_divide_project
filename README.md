# FLEMMS Digital Divide & Functional Literacy Data Pipeline

## Project Overview
This project builds a robust Data Engineering ETL pipeline using the Functional Literacy, Education, and Mass Media Survey (FLEMMS) dataset (focusing on the 2024 study covering 172,800 houses). 

### Problem Statement
Is there a digital divide between different age groups, geographic regions, and educational levels in the Philippines, and to what extent does this digital divide relate to the functional literacy of the population?

## Project Architecture & Directory Structure
- `data/raw/`: Original multi-year metadata and zipped survey folders.
- `data/processed/`: Partitioned and cleaned data separated into `households/` and `individuals/`.
- `data/final/`: Final analysis-ready analytical base tables (ABT).
- `notebooks/`: Jupyter notebooks used for exploratory data analysis and ETL prototyping.
- `src/`: Modular Python scripts for extraction, transformation, and loading.

## Current Progress (Data Engineering Phase)
1. **Ingestion & Partitioning:** Successfully extracted multi-year raw CSV files, handling encoding (`latin-1`) and memory constraints by partitioning data into household and individual directories.
2. **Data Profiling & Cleaning:** Standardized column schemas to `lower_snake_case`, handled tokenizing errors, eliminated duplicates, and filtered down to the target 2024 baseline datasets.

## Folder Structure
flemms_digital_divide_project/
│
├── data/
│   ├── raw/          # Untouched raw survey files & metadata
│   ├── processed/    # Partitioned household and individual CSVs
│   └── final/        # Clean analytical base tables (.parquet)
│
├── notebooks/        # Jupyter notebooks for EDA and ETL prototyping
├── sql/              # Database schemas and analytical queries
├── src/              # Modular Python scripts (extract, transform, load)
├── pipeline.py       # Main pipeline orchestrator
└── requirements.txt  # Project dependencies

# FLEMMS 2024 Digital Divide & Functional Literacy Project

## Project Overview
This Data Engineering project analyzes the **2024 Functional Literacy, Education, and Mass Media Survey (FLEMMS)** dataset from the Philippine Statistics Authority (PSA). The survey covers 172,800 households. The core objective is to investigate whether a digital divide exists across different age groups, geographic regions, and educational levels in the Philippines, and how it correlates with functional literacy.

## System Architecture
The ETL (Extract, Transform, Load) pipeline is built using Python (Pandas) and orchestrated to handle multi-gigabyte survey datasets efficiently.

- **Data Ingestion (`src/extract.py`):** Automated extraction and parsing of raw PUF (Public Use File) datasets, handling legacy encoding (`latin-1`) and tokenization errors.
- **Data Harmonization (`src/transform.py`):** Standardizing column headers to `lower_snake_case`, merging household data (digital access metrics) with individual demographic data (age, education, literacy) using geographic and household keys.
- **Optimized Storage (`src/load.py`):** The final Analytical Base Table is exported as a compressed Apache Parquet file (`flemms_analytical_base_table.parquet`), significantly reducing read times for Data Science modeling.

## Folder Structure
```text
flemms_digital_divide_project/
│
├── data/
│   ├── raw/          # Untouched raw survey files (Ignored in Git)
│   ├── processed/    # Partitioned household and individual CSVs (Ignored)
│   └── final/        # Clean Parquet analytical base tables (Ignored)
│
├── notebooks/        # Jupyter notebooks for EDA and ETL prototyping
├── sql/              # schema.sql documenting final table architecture
├── src/              # Modular ETL Python scripts
│   ├── extract.py
│   ├── transform.py
│   └── load.py
│
├── pipeline.py       # Main orchestrator script to run the ETL
├── requirements.txt  # Project dependencies
└── .gitignore        # Keeps large data files out of version control