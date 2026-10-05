# File format comparison

Table `person_profile`: 650,424 rows x 29 columns. Generated 2026-10-05T05:59:26+00:00 (batch `manual__2026-10-05T05:54:36.567625+00:00`). Times depend on the machine.

| Format | Size (MB) | Write (s) | Read (s) | Column types preserved |
|---|---:|---:|---:|---|
| CSV | 146.52 | 20.88 | 4.52 | no (27 of 29 columns changed type) |
| JSON (records, one per line) | 485.02 | 12.95 | 18.76 | no (27 of 29 columns changed type) |
| Parquet (snappy) | 9.16 | 1.86 | 0.25 | yes |

## Partition pruning

The curated table is partitioned by `region_code`. Reading only region 13:

| Read | Files | Rows | Seconds |
|---|---:|---:|---:|
| All regions | 17 | 650,424 | 0.118 |
| Region 13 only | 1 | 80,320 | 0.017 |
