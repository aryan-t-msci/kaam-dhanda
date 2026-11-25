# Og_URLC02_MR → Subset_17037 → 7,655-row final: complete work log

Covers 20–26 Nov 2026. Purpose: record every step, rule, count and file so the work can be reproduced or handed to another session or LLM.

---

## 1. Result in one table

| Step | Definition | Rows | Running total |
|---|---|---:|---:|
| 1 | Total rows in `Og_URLC02_MR.csv` | – | 82,463 |
| 2 | Excluded: Top 20 issuers (35,986 by issuer ID + 85 confirmed by `FACILITY_ID`) | 36,071 | 46,392 |
| 3 | Excluded: out-of-scope list (4,630) + GREY (573) | 5,203 | 41,189 |
| 4 | Assets worked upon (in the correct_only audit) | 41,189 | 41,189 |
| 5 | Post-processing: recommended issuer = original issuer (subtracted) | 33,534 | 7,655 |
| 6 | Other additions (audit-only facilities): 284 dropped | 0 | **7,655** |

**Final: 7,655 rows = 7,650 unique `FACILITY_ID`s.** The 5 extra rows are repeated IDs (Jardine Matheson, 7-Eleven China - Zhongshan 10/12/40/41/42; both CSV rows are identical and GREEN).

| Final category | Rows | Unique facilities |
|---|---:|---:|
| GREEN | 5,276 | 5,271 |
| GICS_LAVENDER | 1,174 | 1,174 |
| ORANGE | 959 | 959 |
| BLUE | 154 | 154 |
| LIGHT_GREEN | 48 | 48 |
| RED | 44 | 44 |
| **Total** | **7,655** | **7,650** |

GREEN + GICS_LAVENDER + LIGHT_GREEN + ORANGE = 7,457 rows (7,452 facilities).

Final-step arithmetic: 36,071 + 5,203 + 33,534 + 7,655 = 82,463.

---

## 2. Inputs

| Input | What it is |
|---|---|
| `Og_URLC02_MR.csv` | 82,463 rows, 82,382 unique `FACILITY_ID`s (81 IDs repeat), 31 data columns plus an unnamed index (renamed `ORIG_INDEX`) |
| Out-of-scope list (pasted txt) | 59,945 `FACILITY_ID`s |
| `correct_only_FULL_checkpoint_final.xlsx` | First correct_only file (`Review` sheet, 5,565 IDs). Used only in the early coverage checks |
| `correct_only_FULL_checkpoint_20261119_1256_turn9audit_2.xlsx` ("audit_2") | `Review` (42,058 rows, one per `FACILITY_ID`) and `Facility Issuer-Used Reference` sheets. Basis for Steps 4–6 |
| `Master_File_Updated_Issuer_Check_Final_-_Backup.xlsx` ("reference file") | `Sheet1`, about 291k rows, with Issuer Check TP/FP. Used only in the early issuer-mapping check |
| Top 20 issuer list | 20 `DMX_ISSUER_ID` + company-name pairs supplied by the user |
| `LLM_QA_W_Land_Cover_Combined(.parquet / _1.parquet)` | Original dump, 667,029 rows. Used to check original issuers and countries |
| `Subset_17037_Issuer_Remapping_FINAL_SYNCHRONIZED_25Nov2026.xlsx` | 16,952 facilities. The work product that the waterfall had to reconcile to |
| `Subset_17037_FINAL_ISSUER_GICS_CLOSED_25Nov2026.xlsx` ("GICS_CLOSED") | Same 16,952 facilities, later categories and recommended issuers. Source of the final workbook |

Matching keys: Top 20 on `DMX_ISSUER_ID` (company name cross-checked), the out-of-scope list and audit files on `FACILITY_ID`, the reference file on `FACILITY_ID` + `DMX_ISSUER_ID`.

---

## 3. Chronology

### 3.1 Coverage against out-of-scope list and correct_only (20 Nov)
- Of the 82,463 rows, 4,636 were in the out-of-scope list and 5,280 in the first correct_only file; none in both. **72,547 remained.**
- Saved as `Remaining_72k_not_OOS_not_correct_only.xlsx`.

### 3.2 Issuer check from the reference file
- Only **24,794** of the 72,547 had a result in the reference file: FP 24,454, TP 339, DROP 1. Semantics: TP = verified not the issuer's; FP = related to the issuer group.
- **47,753** had no result (45,596 URLC02 and 2,157 Manual_Review). 22 of these have a `FACILITY_ID` in the reference file under a different issuer.
- Split into two separate files: 24,794 in reference; 47,753 not in reference.

### 3.3 audit_2 coverage and the Top 20 waterfall (23 Nov)
- audit_2 covered 36,568 of the 72,547 remaining (50.4%).
- With the Top 20 applied first: Top 20 removed 35,986 rows, out-of-scope 4,630, leaving 41,847, **all** of which are in audit_2. The reference file and "not covered" buckets were both 0.
- Only 6 of the 20 issuers have rows in the CSV: Seven & i (20,753), Zensho (6,565), H World (5,879), ENEOS (2,787), Starbucks (1), BGF Retail (1). All matched on both ID and name.
- A notebook was built to reproduce the waterfall (see §6).

### 3.4 Issuer used vs original issuer (audit_2)
- `Facility Issuer-Used Reference` `ISSUER_ID_USED` vs CSV `DMX_ISSUER_ID`: 41,848 matched CSV rows, **16,768 differ**, 25,080 same.

### 3.5 Redefined Steps 5 and 6 (user instruction)
- **Step 5 (post-processing):** rows where audit_2's `ISSUER_ID_USED` equals the CSV `DMX_ISSUER_ID`. Subtracted. **25,080 rows.**
- **Step 6 (other additions):** audit_2 `FACILITY_ID`s that are not in the CSV at all. Added. **285 facilities.**
- Final then = 16,768 + 285. One of the 16,768 was a Zensho row already excluded at Step 2, so the waterfall gave 16,767 + 285 = 17,052 rows (17,037 unique IDs).

### 3.6 85 facilities moved into Step 2
- 85 Jardine Matheson (7-Eleven Hong Kong) facilities were missing from the closed subset file. The user confirmed they belong to the Top 20 (in the dump they appear under Seven & i as well). They were excluded by `FACILITY_ID`, because their CSV issuer is Jardine Matheson.
- Result: Step 2 = 36,071, Step 4 = 41,762, Step 5 = 25,080, changed rows 16,682, + 285 additions = **16,967 rows = 16,952 unique facilities**. This matched the FINAL_SYNCHRONIZED subset file exactly.
- Step 4 was renamed "Assets worked upon".
- A check against the original dump confirmed that none of the 16,952 facilities has a Top 20 issuer as original or recommended issuer.

### 3.7 Row-level classification files
- `Og_URLC02_MR_with_STEP_and_CATEGORY.csv`: all 82,463 rows with `STEP` and `CATEGORY` (category from the GICS_CLOSED `Review` sheet, filled only for the 16,967 final rows). The 285 additions went into a separate CSV, because they are not in the 82,463.

### 3.8 Recommended issuer vs original dump issuer (25 Nov)
- For the 16,952 facilities in GICS_CLOSED, comparing the recommended issuer with the original dump issuer gave **8,445 same** (no issuer remap needed) and **8,507 different**.
- Same-issuer set by category: 8,385 were already GREEN; 43 GICS_LAVENDER, 16 LIGHT_GREEN and 1 BLUE (60 not GREEN).
- The ofi.com check: 69 facilities, all ORANGE, original Olam Group Limited (dump) / OFI Group Limited (`Review`), recommended Olam International Limited (`IID000000002127967`). Pending DMX correction: add `https://www.ofi.com/` to Olam International.
- A step in which the 8,445 were set to GREEN was made and then superseded by §3.9.

### 3.9 8,445 moved to Step 5
- The 8,445 same-issuer facilities were moved into Step 5: 8,454 CSV rows (8,444 facilities; 10 extra rows are repeated IDs). The 8,445th facility is audit-only, so Step 6 became 284.
- Step 5 = 25,080 + 8,454 = **33,534**. Final = 16,682 − 8,454 + 284 = **8,512 rows = 8,507 facilities**.
- The subset workbook was synchronized (see §5).

### 3.10 GREY into Step 3, additions dropped
- 573 GREY rows moved from the final set into Step 3 (breakdown only). They were all in the retained set; Step 5 was unaffected.
- The 284 additions were dropped (6 of them were GREY).
- Final: 7,655 rows / 7,650 facilities.
- The workbook was filtered to the same 7,650 facilities. The 5 repeated Zhongshan rows were then added back (flagged), giving 7,655 rows.

---

## 4. Rules and decisions applied

1. Top 20: match on `DMX_ISSUER_ID`; company name confirmed. Plus the 85 facilities by `FACILITY_ID`.
2. Exclusions are sequential and each row exits at the first step that catches it.
3. Step 3 includes GREY only in the breakdown. The filtered workbook also excludes GREY facilities.
4. Step 5 evolved: first audit_2 `ISSUER_ID_USED` = CSV issuer; later also facilities whose recommended issuer in GICS_CLOSED is among the issuers carried for that facility in the original dump.
5. Counts are rows unless stated as facilities. Rows and unique facilities differ by the 5 repeated Jardine Matheson IDs in the final set.
6. Excluded or moved GREY rows have a blank `CATEGORY` in the step-category file; the `STEP` text still says GREY.
7. Step-5 rows keep a blank `CATEGORY`.

---

## 5. Workbook synchronization (`Subset_17037_FINAL_ISSUER_GICS_CLOSED_25Nov2026_SYNCED_*`)

Built from the original GICS_CLOSED file, so earlier edits do not carry over. Facilities removed: 8,445 same-issuer + 284 additions + 573 GREY = 9,302.

| Sheet | Action | Rows after (7,650 version) |
|---|---|---:|
| `Review` | deleted removed facilities (9,302) | 7,650 |
| `Facility Issuer-Used Reference` | same | 7,650 |
| `Data Corrections` | rows by `facility_id` removed (14) | 1,121 (from 1,135) |
| `DMX Corrections` | no overlap, nothing removed | 44 |
| `DMX GICS Only Corrections` | 4 rows whose facilities were all removed (incl. Waltons, 43 facilities) | 102 (from 106) |
| `Other Inputs Needed` | 95 removed | 231 |
| `REVIEW Audit` | 654 removed | 1,351 |
| `Facility Changes` | 4,476 removed | 26,483 |
| `Closeout Decisions` | 1,106 removed | 5,080 |
| `Correction Assessments` | 21 removed | 4,031 |
| `Country Audit` | 9 removed | 6 |
| `Audit Findings` | 26 removed (single-facility references) | 185 |
| `N8 Issuer Routes` | 2 rows removed, 1 recounted | 88 |
| `Issuer Scope Evidence` | 19 removed, 8 recounted | 193 |
| `Applied Closure` | 74 table rows removed; title and formula ranges updated | 253 |
| `Open Items` | 22 items removed; `Review` row references remapped | 44 |

Final version `…SYNCED_7655rows.xlsx` adds the 5 duplicate rows at the end of `Review` and `Facility Issuer-Used Reference`, flagged `Y` in `DUPLICATE_ROW_IN_SOURCE_CSV`; the `Applied Closure` title reads "7,655 rows | 7,650 unique facilities".

Checks run on each version: every sheet keyed by facility has no removed IDs; no sheet references a facility missing from `Review`; `Review` and the reference sheet carry the same IDs and categories; the facility counts in the correction sheets match their lists; all `Open Items` references resolve to the right facilities.

---

## 6. Files produced (final ones in bold)

| File | Content |
|---|---|
| **`Og_URLC02_MR_facility_step_category.csv` / `.xlsx`** | All 82,463 rows with `STEP_NO`, `STEP`, `CATEGORY` (final classification) |
| **`Og_URLC02_MR_count_breakdown_v4.csv`** | Step-wise and category breakdown (long form) |
| `Og_URLC02_MR_with_STEP_and_CATEGORY_v4.csv` | Same classification with all 33 original columns |
| `Step6_additions_not_in_CSV_285_v4.csv` | The 285 audit-only facilities (284 tagged dropped, 1 tagged Step 5) |
| **`Subset_17037_FINAL_ISSUER_GICS_CLOSED_25Nov2026_SYNCED_7655rows.xlsx`** | Final filtered workbook |
| `…SYNCED_7650.xlsx` / `…SYNCED_8223.xlsx` / `…SYNCED_8507.xlsx` | Earlier filtered versions (7,650 unique; 8,223; 8,507 facilities) |
| `Facility_Issuer_Used_8223_step4_facilities.xlsx` | Filtered reference sheet (8,223 facilities, before the GREY move) |
| `Duplicate_FACILITY_ID_check.xlsx` | The 15 repeated IDs (39 CSV rows) vs the recommended issuer and category |
| `Og_URLC02_MR_final_breakdown_v4.ipynb` | Waterfall notebook (Top 20 + 85 IDs, audit_2 Step 5 rule). **Not updated for §3.8–3.10** |
| `Remaining_72k_*.xlsx` | Early splits of the 72,547 remaining rows |

---

## 7. Open points and caveats

- **Notebook:** `Og_URLC02_MR_final_breakdown_v4.ipynb` reproduces Steps 1–6 on the audit_2 basis. It does not include the dump-based Step 5 extension, the GREY move, or the dropped additions. The final CSV files are the authoritative result.
- **Facility vs row basis:** Step 5 and Step 6 move facilities (8,445) as rows (8,454, 1). Quote rows with the step table and facilities with the workbook.
- **Extra rows from the facility rule:** 176 of the 8,454 CSV rows have their own CSV issuer different from the recommended issuer; the recommended issuer appears for the same facility under another dump issuer (for example the 1st Source / Federal Realty rows).
- **13 facilities** with several original issuers in the dump have a recommended issuer that matches none of them.
- **OFI/Olam:** the dump lists the original issuer of the 69 ofi.com facilities as Olam Group Limited, while the `Review` sheet lists OFI Group Limited. The recommendation (Olam International) is the same either way.
- **Narrative text** in `Applied Closure`, `Open Items` and `Rules & M3 Deviations` is not rewritten (for example the GICS count of 106, the 327 dispositions and the Waltons note). `Correction Dispositions` still mentions removed facilities in its history text.
- **Category counts** on `Applied Closure` are formulas that recalculate when the workbook is opened in Excel.
- **Later issuer values:** GICS_CLOSED has different `ISSUER_ID_USED` than audit_2 for 9,613 of the 16,952 facilities. Step 5 as defined follows audit_2 first and the dump comparison second, as described in §3.5 and §3.8.
- **Country check (separate):** facilities `90f045cf…cbf8` (FIFGROUP Branch - Makassar 11) and `ffe9495e…bbe612` (Eastkal Seaport & Logistics) have a blank `ASSET_COUNTRY` in the parquet. Both are in Indonesia (IDN) per address and coordinates; the subset workbook already records IDN.
