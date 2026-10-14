# File format comparison

Table `person_profile`: 650,424 rows x 29 columns. Generated 2026-10-14T09:10:23+00:00 (batch `manual__2026-10-14T09:06:01.362592+00:00`). Times depend on the machine.

| Format | Size (MB) | Write (s) | Read (s) | Column types preserved |
|---|---:|---:|---:|---|
| CSV | 146.52 | 22.75 | 3.88 | no (27 of 29 columns changed type) |
| JSON (records, one per line) | 485.02 | 10.53 | 19.12 | no (27 of 29 columns changed type) |
| Parquet (snappy) | 9.16 | 1.87 | 0.23 | yes |

## Partition pruning

The curated table is partitioned by `region_code`. Reading only region 13:

| Read | Files | Rows | Seconds |
|---|---:|---:|---:|
| All regions | 17 | 650,424 | 0.168 |
| Region 13 only | 1 | 80,320 | 0.017 |
