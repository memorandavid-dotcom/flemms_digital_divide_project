# File format comparison

Table `person_profile`: 650,424 rows x 29 columns. Generated 2026-10-05T09:17:15+00:00 (batch `manual__2026-10-05T09:13:06.913597+00:00`). Times depend on the machine.

| Format | Size (MB) | Write (s) | Read (s) | Column types preserved |
|---|---:|---:|---:|---|
| CSV | 146.52 | 19.8 | 4.48 | no (27 of 29 columns changed type) |
| JSON (records, one per line) | 485.02 | 32.52 | 19.51 | no (27 of 29 columns changed type) |
| Parquet (snappy) | 9.16 | 1.27 | 0.13 | yes |

## Partition pruning

The curated table is partitioned by `region_code`. Reading only region 13:

| Read | Files | Rows | Seconds |
|---|---:|---:|---:|
| All regions | 17 | 650,424 | 0.089 |
| Region 13 only | 1 | 80,320 | 0.016 |
