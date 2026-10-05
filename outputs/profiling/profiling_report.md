# Source profiling report

Generated 2026-10-05T05:55:58+00:00 (batch `manual__2026-10-05T05:54:36.567625+00:00`) from the raw files, before any cleaning.

## v1_household — `FLEMMS PUF 2024 Volume1 - HOUSEHOLD.CSV`

- Rows: **177,656**, columns: **8**
- Fully duplicated rows: **0**
- Columns ≥50% blank: 0
- Columns mixing numbers and text: none

| Column | Type | Missing % | Distinct | Min | Max | Mean |
|---|---|---:|---:|---:|---:|---:|
| REG | numeric | 0.0 | 17 | 1.0 | 19.0 | 9.647 |
| REG2 | numeric | 0.0 | 18 | 1.0 | 19.0 | 10.008 |
| PRV | numeric | 0.0 | 118 | 1.0 | 999.0 | 187.278 |
| HHID | numeric | 0.0 | 177,656 | 1.0 | 177656.0 | 88828.5 |
| URBANITY | numeric | 0.0 | 3 | 1.0 | 3.0 | 1.504 |
| PSU | numeric | 0.0 | 2,126 | 1.0 | 5236.0 | 565.592 |
| INTVW | numeric | 0.0 | 1 | 1.0 | 1.0 | 1.0 |
| RFACT | numeric | 0.0 | 10,614 | 5.2178888 | 2137.7371 | 156.393 |

## v1_household_questions — `FLEMMS PUF 2024 Volume1 - RTF1.CSV`

- Rows: **177,656**, columns: **61**
- Fully duplicated rows: **0**
- Columns ≥50% blank: 5 (ADULTS, GUARDIAN, TOILET_PUBLIC, ODL_SOFTWARE, ODL_TECHNOLOGY)
- Columns mixing numbers and text: none

| Column | Type | Missing % | Distinct | Min | Max | Mean |
|---|---|---:|---:|---:|---:|---:|
| REG | numeric | 0.0 | 17 | 1.0 | 19.0 | 9.647 |
| REG2 | numeric | 0.0 | 18 | 1.0 | 19.0 | 10.008 |
| PRV | numeric | 0.0 | 118 | 1.0 | 999.0 | 187.278 |
| HHID | numeric | 0.0 | 177,656 | 1.0 | 177656.0 | 88828.5 |
| URBANITY | numeric | 0.0 | 3 | 1.0 | 3.0 | 1.504 |
| PSU_F1 | numeric | 0.0 | 2,126 | 1.0 | 5236.0 | 565.592 |
| BENEFICIARY_4PS | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.852 |
| CHILDREN_04 | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.815 |
| ADULTS | numeric | 81.53 | 2 | 1.0 | 2.0 | 1.345 |
| GUARDIAN | numeric | 87.89 | 6 | 1.0 | 9.0 | 2.517 |
| CHILD_FACILITY | numeric | 0.0 | 3 | 1.0 | 3.0 | 1.852 |
| BUILDING | numeric | 0.0 | 7 | 1.0 | 9.0 | 1.172 |
| ROOF | numeric | 0.0 | 9 | 1.0 | 9.0 | 1.313 |
| WALL | numeric | 0.0 | 10 | 1.0 | 99.0 | 2.592 |
| FLOOR_FINISH | numeric | 0.0 | 8 | 1.0 | 9.0 | 2.41 |
| FLOOR_MAIN | numeric | 0.0 | 7 | 1.0 | 9.0 | 1.412 |
| TENURE | numeric | 0.0 | 7 | 1.0 | 7.0 | 2.153 |
| ELECTRICITY | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.043 |
| HH_REF | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.519 |
| HH_AIRCON | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.829 |
| HH_WASHING | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.525 |
| HH_OVEN | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.756 |
| HH_RADIO | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.729 |
| HH_ANATV | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.901 |
| HH_DIGITV | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.461 |
| HH_AUDIO | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.802 |
| HH_LANDLINE | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.931 |
| HH_BASICPHONE | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.802 |
| HH_SMARTPHONE | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.186 |
| HH_TABLET | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.892 |
| HH_PC | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.817 |
| HH_CAR | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.909 |
| HH_VAN | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.983 |
| HH_JEEP | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.992 |
| HH_TRUCK | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.987 |
| HH_MOTOR | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.552 |
| HH_EBIKE | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.978 |
| HH_TRICYCLE | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.891 |
| HH_BIKE | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.916 |
| HH_PEDICAB | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.99 |
| HH_MBOAT | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.973 |
| HH_NBOAT | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.985 |
| HH_TRACTOR | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.992 |
| HH_ANIMAL | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.949 |
| HH_CABLE | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.755 |
| HH_CABNET | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.787 |
| HH_NOCABNET | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.898 |
| HH_MOBSUB | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.541 |
| HH_VSTREAM | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.787 |
| HH_MSTREAM | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.737 |
| DRINK_WATER | numeric | 0.0 | 16 | 11.0 | 99.0 | 48.394 |
| OTHERS_WATER | numeric | 0.0 | 16 | 11.0 | 99.0 | 17.404 |
| TOILET | numeric | 0.0 | 13 | 11.0 | 95.0 | 15.114 |
| TOILET_LOC | numeric | 2.77 | 3 | 1.0 | 3.0 | 1.285 |
| TOILET_SHARE | numeric | 2.77 | 2 | 1.0 | 2.0 | 1.848 |
| TOILET_PUBLIC | numeric | 85.24 | 2 | 1.0 | 2.0 | 1.06 |
| ODL_FAM | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.647 |
| ICT_EQUIP | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.658 |
| ODL_SOFTWARE | numeric | 65.76 | 2 | 1.0 | 2.0 | 1.419 |
| ODL_TECHNOLOGY | numeric | 65.76 | 2 | 1.0 | 2.0 | 1.135 |
| HH_RFACT | numeric | 0.0 | 10,614 | 5.2178888 | 2137.7371 | 156.393 |

## v1_member — `FLEMMS PUF 2024 Volume1 - MEMBER.CSV`

- Rows: **650,424**, columns: **45**
- Fully duplicated rows: **0**
- Columns ≥50% blank: 15 (MOTHER_LNO, FATHER_LNO, OF_PRESENT, ATTEND_SCHOOL, ATTEND_GRADE_LEVEL, ATTEND_GRADE, MODETRVL1, MODETRVL2, MODETRVL3, NATT_REASON, SHS, SHS_TRACK, WORK_TYPE_MAJOR, WORK_CLASS, NOWORK_REASON)
- Columns mixing numbers and text: none

| Column | Type | Missing % | Distinct | Min | Max | Mean |
|---|---|---:|---:|---:|---:|---:|
| REG | numeric | 0.0 | 17 | 1.0 | 19.0 | 9.668 |
| REG2 | numeric | 0.0 | 18 | 1.0 | 19.0 | 10.025 |
| PRV | numeric | 0.0 | 118 | 1.0 | 999.0 | 182.287 |
| HHID | numeric | 0.0 | 177,656 | 1.0 | 177656.0 | 88911.049 |
| URBANITY | numeric | 0.0 | 3 | 1.0 | 3.0 | 1.511 |
| PSU_MEM | numeric | 0.0 | 2,126 | 1.0 | 5236.0 | 568.135 |
| LNO | numeric | 0.0 | 23 | 1.0 | 23.0 | 2.826 |
| SEX | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.497 |
| AGE | numeric | 0.0 | 100 | 0.0 | 99.0 | 31.997 |
| REL | numeric | 0.0 | 26 | 1.0 | 26.0 | 3.895 |
| MOTHER | numeric | 0.0 | 5 | 1.0 | 99.0 | 55.655 |
| MOTHER_LNO | numeric | 57.28 | 18 | 1.0 | 20.0 | 2.012 |
| FATHER | numeric | 0.0 | 5 | 1.0 | 99.0 | 61.526 |
| FATHER_LNO | numeric | 63.37 | 17 | 1.0 | 17.0 | 1.31 |
| ETHNICITY | numeric | 0.0 | 274 | 1.0 | 998.0 | 152.243 |
| MSTAT | numeric | 0.0 | 8 | 1.0 | 8.0 | 1.773 |
| OF | numeric | 0.0 | 5 | 1.0 | 5.0 | 4.954 |
| OF_PRESENT | numeric | 98.8 | 2 | 1.0 | 2.0 | 1.874 |
| ATTEND_SCHOOL | numeric | 51.25 | 4 | 1.0 | 4.0 | 2.083 |
| ATTEND_GRADE_LEVEL | numeric | 67.76 | 9 | 0.0 | 8.0 | 2.146 |
| ATTEND_GRADE | numeric | 67.76 | 41 | 1000.0 | 80010.0 | 23075.7 |
| MODETRVL1 | numeric | 67.76 | 10 | 1.0 | 19.0 | 2.858 |
| MODETRVL2 | numeric | 85.25 | 9 | 1.0 | 19.0 | 4.403 |
| MODETRVL3 | numeric | 93.59 | 9 | 1.0 | 19.0 | 5.613 |
| NATT_REASON | numeric | 83.49 | 20 | 1.0 | 96.0 | 8.461 |
| BASIC_LIT | numeric | 7.17 | 2 | 1.0 | 2.0 | 1.055 |
| BASIC_NUM | numeric | 7.17 | 2 | 1.0 | 2.0 | 1.047 |
| HGC_LEVEL | numeric | 7.17 | 9 | 0.0 | 8.0 | 2.615 |
| HGC_GRADE | numeric | 7.17 | 609 | 0.0 | 89999.0 | 27902.54 |
| DAYCARE | numeric | 10.9 | 4 | 1.0 | 4.0 | 2.61 |
| KINDER | numeric | 12.91 | 4 | 1.0 | 4.0 | 2.45 |
| SHS | numeric | 76.68 | 4 | 1.0 | 4.0 | 3.406 |
| SHS_TRACK | numeric | 95.06 | 4 | 1.0 | 4.0 | 1.455 |
| ALS | numeric | 7.17 | 4 | 1.0 | 4.0 | 2.979 |
| WORK | numeric | 26.73 | 2 | 1.0 | 2.0 | 1.468 |
| WORK_TYPE_MAJOR | numeric | 61.04 | 44 | 1.0 | 99.0 | 61.505 |
| WORK_CLASS | numeric | 61.04 | 7 | 0.0 | 6.0 | 1.926 |
| NOWORK_REASON | numeric | 65.69 | 10 | 1.0 | 96.0 | 4.874 |
| DIFF_SEEING | numeric | 7.17 | 4 | 1.0 | 4.0 | 1.095 |
| DIFF_HEARING | numeric | 7.17 | 4 | 1.0 | 4.0 | 1.044 |
| DIFF_WALKING | numeric | 7.17 | 4 | 1.0 | 4.0 | 1.054 |
| DIFF_REMEMBERING | numeric | 7.17 | 4 | 1.0 | 4.0 | 1.043 |
| DIFF_SELFCARE | numeric | 7.17 | 4 | 1.0 | 4.0 | 1.034 |
| DIFF_COMMUNICATING | numeric | 7.17 | 4 | 1.0 | 4.0 | 1.028 |
| MEM_RFACT | numeric | 0.0 | 4,006 | 3.1384616 | 1453.8188 | 176.16 |

## v1_literacy — `FLEMMS PUF 2024 Volume1 - RTF2.CSV`

- Rows: **610,590**, columns: **28**
- Fully duplicated rows: **0**
- Columns ≥50% blank: 4 (READING59, WRITING59, COMPUTE59, LLEVEL59)
- Columns mixing numbers and text: none

| Column | Type | Missing % | Distinct | Min | Max | Mean |
|---|---|---:|---:|---:|---:|---:|
| REG | numeric | 0.0 | 17 | 1.0 | 19.0 | 9.646 |
| REG2 | numeric | 0.0 | 18 | 1.0 | 19.0 | 10.006 |
| PRV | numeric | 0.0 | 118 | 1.0 | 999.0 | 183.289 |
| HHID | numeric | 0.0 | 177,656 | 1.0 | 177656.0 | 88715.044 |
| URBANITY | numeric | 0.0 | 3 | 1.0 | 3.0 | 1.509 |
| PSU_F2 | numeric | 0.0 | 2,126 | 1.0 | 5236.0 | 568.469 |
| LNO_F2 | numeric | 0.0 | 21 | 1.0 | 21.0 | 2.688 |
| RESULT_CODE_F2 | numeric | 0.0 | 6 | 1.0 | 9.0 | 1.211 |
| RESP_AGREE_F2 | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.062 |
| READ_IND_F2 | numeric | 6.24 | 3 | 1.0 | 3.0 | 1.055 |
| AGE_F2 | numeric | 0.0 | 95 | 5.0 | 99.0 | 33.937 |
| SEX_F2 | numeric | 0.0 | 2 | 1.0 | 2.0 | 1.498 |
| REL_F2 | numeric | 0.0 | 26 | 1.0 | 26.0 | 3.795 |
| HGC_GRADE_F2 | numeric | 1.11 | 609 | 0.0 | 89999.0 | 27902.54 |
| READING59 | numeric | 90.74 | 2 | 1.0 | 2.0 | 1.118 |
| WRITING59 | numeric | 90.74 | 2 | 1.0 | 2.0 | 1.21 |
| COMPUTE59 | numeric | 90.74 | 2 | 1.0 | 2.0 | 1.23 |
| LLEVEL59 | numeric | 90.74 | 3 | 0.0 | 2.0 | 1.559 |
| READING | numeric | 15.5 | 2 | 1.0 | 2.0 | 1.037 |
| WRITING | numeric | 15.5 | 2 | 1.0 | 2.0 | 1.063 |
| COMPUTE | numeric | 15.5 | 2 | 1.0 | 2.0 | 1.099 |
| COMPRE | numeric | 23.25 | 2 | 1.0 | 2.0 | 1.306 |
| LLEVEL10OVER | numeric | 15.5 | 4 | 0.0 | 3.0 | 2.469 |
| LLEVEL5OVER | numeric | 6.24 | 3 | 0.0 | 2.0 | 1.81 |
| FLLEVEL | numeric | 23.25 | 4 | 0.0 | 3.0 | 2.568 |
| BLITERATE | numeric | 6.24 | 2 | 1.0 | 2.0 | 1.112 |
| FLITERATE | numeric | 23.25 | 2 | 1.0 | 2.0 | 1.306 |
| RESP_RFACT_F2 | numeric | 0.0 | 232,692 | 0.0 | 3353.35083008 | 169.445 |
