# RemapSubset – assigned-issuer verdict: handoff for another session

**File:** `RemapSubset_M3_Issuer_Verification_20261117.xlsx`, sheet `Row_Verdicts` (2,209 rows × 62 columns).

**Question answered, ignoring ACTION:** is the assigned `DMX_ISSUER_ID` / `COMPANY_NAME` the right owner of the facility, and is it the ID M3 v3.2 would collect it under?

## 1. Inputs and basis
- **RemapSubset.xlsx:** 2,209 facility rows. They were moved off an original issuer onto a subsidiary whose domain hosts RELEVANT_URL.
  - The original (input) issuer is the first IID in `URL_CONSISTENCY_GROUPING`.
  - 22 rows have no grouping. For those, the input issuer is the assigned issuer itself.
- **sec_master_20260828.parquet:** hierarchy (immediate `parent_issuer_id` walk), URLs, GICS sector, domicile.
- **M3 v3.1 doc + v3.2 N5a (user decision):** if the input issuer's GICS sector is Energy, Materials, Industrials or Utilities, every descendant with its own Issuer ID is collected at its own ID (O7). The URL, hostname and type tests are bypassed.
- **User decision:** an equity-listed child is its own Input Issuer (own N1). It is kept at the child ID, not skipped.
- **Standing rules:**
  - Lifco attribution is held at group level.
  - Divested facility → not the group's.
  - Regulator registers are inadmissible as evidence.
  - Owner rule: use the most granular in-tree owner/operator that has its own ID and a URL.

## 2. The category column (`Assigned_Issuer_Category`, green band)
Decision order per row:

| # | Category | Rule | Assigned_Owner_Correct | Assigned_M3_Consistent |
|---|---|---|---|---|
| 1 | `1_RIGHT_OWNER_M3_CONSISTENT` | Ownership verdict = CORRECT, CORRECT - PENDING DIVESTMENT or CORRECT - SOURCE INADMISSIBLE, **and** M3 outcome at the assigned ID ∈ {O3/O4, O6, O7, Own N1} | Yes | Yes |
| 2 | `2_RIGHT_OWNER_M3_SKIPPED_CHILD` | Same ownership verdicts, but M3 = **O5**: the input sector is not N5a, and either the child's DMX URL hostname ≠ the input issuer's hostname or the child has no DMX URL | Yes | No |
| 3 | `3_RIGHT_GROUP_WRONG_ENTITY` | Facility is in the same group, but another entity should hold it (`Final_Issuer_IID`). Covers a more granular operator, a separately listed group company, and the Lifco group rule | No | n/a |
| 4 | `4_NOT_THE_OWNER` | Unrelated domain owner, divested out of the group, or a sold residential asset | No | n/a |
| 5 | `5_OWNERSHIP_UNRESOLVED_JV` | 50/50 JV, control not established | Unresolved | n/a |

`Category_Reason` gives a one-line reason for each row.

## 3. Counts (live in sheet `Category_Breakdown`)

| Category | Rows | % | High | Medium | Low |
|---|---|---|---|---|---|
| 1 Right owner, M3-consistent | 1,539 | 69.7% | 856 | 673 | 10 |
| 2 Right owner, M3 skips child (O5) | 332 | 15.0% | 257 | 54 | 21 |
| 3 Right group, wrong entity | 21 | 1.0% | 4 | 8 | 9 |
| 4 Not the owner | 5 | 0.2% | 4 | 1 | 0 |
| 5 Unresolved JV | 312 | 14.1% | 0 | 312 | 0 |
| **Total** | **2,209** | 100% | 1,121 | 1,048 | 40 |

Roll-ups:
- **Right owner (1+2): 1,871 (84.7%).**
- Right owner and M3-consistent (1): 1,539 (69.7%).
- Not right (3+4): 26 (1.2%).
- Unresolved: 312 (14.1%).

### What sits in each category
- **Cat 1 (1,539)**, by M3 outcome:
  - O7 via N5a: 1,401. Largest groups are CK Hutchison (Superdrug 488, Kruidvat 514, Drogas 29), Travis Perkins 59, Mota-Engil/Suma 28, Recruit/Unique 29 and Bidvest/PHS 16.
  - Own N1 listed child: 109 (Clínica Baviera 94, Gulf Insurance Group 5, Makuake 5, Route Mobile 3, Safaricom 1, IONOS 1).
  - Bangchak as BCPG's parent: 21.
  - Assigned = input issuer: 8 (Brookfield Corp offices 6, Nan Ya Plastics 1, BNP Paribas India 1).
  - Note: this category also holds IXOM (owner right, source inadmissible), Cutlite Penta (sale to TRUMPF signed, not closed), and Black Construction (owner right, but the address is a P.O. Box only).
- **Cat 2 (332):** non-N5a input issuers. The biggest are Daito Trust → Housecom (179), Vonovia → BUWOG (20), Fairfax children (19: Allied World, Odyssey, Colonnade, Zenith), Pepco → Dealz (15), BNP children (11) and Asahi subsidiaries (11). The rest are 1–8 rows each across Brown & Brown, NTV, ProSieben, Daiwabo, Quebecor, Trip.com, Thermo Fisher and others.
- **Cat 3 (21):**

  | Rows | Assigned | Should be |
  |---|---|---|
  | 14 | Brookfield Corporation (rows labelled "Brookfield Wealth Solutions") | Brookfield Wealth Solutions Ltd., IID000000005045583 (no DMX parent link) |
  | 3 | Brokk AB | Lifco AB (publ), IID000000002715781 (Lifco rule) |
  | 1 | London Luton Airport Group | London Luton Airport Operations Ltd, IID000000002437467 (the operator) |
  | 1 | Skyscanner Holdings (UK row) | Skyscanner Ltd, IID000000005151915 |
  | 2 | Chalkfree Ltd | UK office → Promethean Limited, IID000000002589679; DE office → Promethean World Limited, IID000000002587071 |

- **Cat 4 (5):**

  | Assigned | Reason | Correct ID |
  |---|---|---|
  | Carglass NZ | lasergroup.co.nz is Laser Plumbing & Electrical NZ, absent from DMX | none |
  | EFCO LLC | efcoforms.com is EFCO formwork, not Apogee; absent from DMX | none |
  | Riello S.p.A. and Riello Poland | Sold to Ariston (closed 1 Jul 2026); DMX is stale | none (acquirer in DMX: Ariston Holding N.V., IID000000005073588) |
  | Hongkong Land Holdings ("The Marq" row) | Sold condo units, owned by individual buyers | n/a |

- **Cat 5 (312):** Rossmann spol. s r.o. (CZ, 179) and Rossmann Magyarország (HU, 133). CK Hutchison's release describes Rossmann Central Europe as a 50/50 A.S. Watson / Rossmann family JV, yet DMX chains it as controlled. Rule 6.5 participation inclusion fails for retail. The evidence is from 2004, so the current shareholding needs confirming.

## 4. Confidence (`Ownership_Confidence` = `Final_Confidence`)
- **High:** DMX link present, URL on the assigned issuer's DMX domain (PATH/FQDN/ROOT ladder), consistent name and address, no ownership change.
- **Medium:** one limiter.
- **Low:** two or more limiters, or a P.O. Box / country-only address.
- `Confidence_Limiters` names them. The common ones:
  - assigned issuer has no DMX URL (61 rows)
  - alternate or brand domain (ROOT ONLY)
  - city- or country-only address
  - legal/privacy page, dealer-finder page, or multi-URL cell
  - facility belongs to a sub-company not in DMX
- `(info)` items, such as a country ≠ domicile, do not lower confidence.

## 5. Other columns a later session will need
- `Input_Issuer_IID/Name/GICS_Sector/DMX_URL`: the original issuer and its routing inputs.
- `Hierarchy_Path`: assigned → input issuer chain.
- `Ladder_Level` / `Ladder_Matched_URL`: RELEVANT_URL vs the assigned issuer's DMX URL.
- `Ownership_Verdict`: finer verdict behind the category. `Ownership_Remark`: reasoning. `Evidence_Source`: link.
- `M3_Route`, `M3_Outcome`, `N5a_Applies`, `Listed_Own_N1`: the M3 path.
  - For cat-3 rows these are evaluated on the **correct** entity, not the assigned one.
- `Suggested_Issuer_Check`: all 73 `FINAL_SUGGESTED_ISSUER` values that differ from DMX_ISSUER_ID are wrong.
- `DMX_Issue`: reference-data defects (930 rows).
- `Final_Action` / `Final_Issuer_*`: the action layer. It is not needed for the category question.

## 6. Limits and open items
- The N2/N8 entity-type gates are untested, because secmaster has no MSCI type/subtype column.
- Pairs without targeted web research rest on the secmaster link plus the child's own first-party site. Not all 762 URLs were opened live.
- Open:
  - Rossmann JV shareholding (cat 5).
  - Cutlite Penta: re-check after the TRUMPF closing.
  - Brookfield Wealth Solutions: re-map after its merger with Brookfield closes (expected end-2026).
  - Housecom franchise vs direct stores is not resolved row by row.
  - BUWOG development projects: sold-out vs planned, under the user's BUWOG rule.

## 7. Reproduce
Scripts are in the session work directory (container-local, may not persist):
1. `det.py` / `det2.py`: host index + ladder.
2. `gran.py`: granular name match.
3. `notes.py`: pair research.
4. `verdict.py`: verdicts + M3.
5. `category.py`: this category.
6. `build_xlsx.py`: workbook.

The logic in sections 2–4 is enough to rebuild them.
