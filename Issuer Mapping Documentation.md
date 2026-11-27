# MSCI Issuer Mapping Activity: Methodology, Rules, and Record of Work

**Scope:** Issuer mapping verification for 5,565 facility-level rows whose remapping was not only correct, but also consistent as per M3. Previous iteration had correct remappings, but due to not being in line with M3, they would either revert back to their originally assigned issuer (no remapping needed) or would later on introduce rework, leading to omission.

**Final checkpoint:** `correct_only_FULL_checkpoint_20261118_0454.xlsx`

**Status at time of writing:** 2,820 rows pending; 331 rows left in `REVIEW` pending user judgment calls. Two standing open questions (Q12, Q23) resolved. Several smaller open questions are still awaiting a decision.

---

## 1. What this audit was checking

Each row in `correct_only_rows.xlsx` represents one physical facility (a store, office, plant, branch, etc.) that MSCI's M3 process had already mapped to a specific issuer (company) in `secmaster`, MSCI's security/issuer reference database, and had marked **CORRECT**. This audit independently re-checked that mapping, one row at a time, against what is true today:

1. **Is the facility still there**, as described, at the URL the row points to (`RELEVANT_URL`)?
2. **Who actually owns/operates it**, according to primary evidence (the company's own site, legal filings, registries)?
3. **Does that match the issuer M3 currently has assigned?** If not, is the correct issuer present in `secmaster`, and does DMX (the data layer M3's mapping lives in) already carry the link needed to fix it?

The output is a specific recommended action for every row: a color category (§2), a plain-English `M3_ACTION` describing what M3 would do today given the data as it stands, and, where something needs fixing, a `DMX_ACTION` describing the specific, minimal correction needed (never a brand-new entity; see the no-new-entity rule in §4).

## 2. Category taxonomy

| Category | Meaning |
| --- | --- |
| **GREEN** | Owner is in secmaster, in the assigned hierarchy, and the currently assigned issuer is correct and consistent with M3. |
| **ORANGE** | A different issuer is correct, but **DMX does not yet have the link**: either the correct issuer needs a parent link added, or the owner is in secmaster but sits outside the assigned issuer's hierarchy. |
| **LIGHT_GREEN** | The real owner is **not** in secmaster as its own entity, but its hostname matches the *assigned* issuer's own URL, so it is most likely an unlisted brand/subsidiary of that issuer and there is no better entity to reassign to. |
| **RED** | Facility not confirmed present on `RELEVANT_URL` (absent, unclear, or blocked), or out of scope (franchisee/dealer/client premises/tenant), or attribution genuinely can't be pinned to any issuer. |
| **REVIEW** | Can't be settled confidently from the available evidence. Always carries a `REVIEW_FLAG`/`REVIEW_REASON` explaining why, rather than being forced into a color. |


## 3. Method: how each row was checked

- **Human-style UI checks through Playwright.** Rows were verified by operating a real, rendered browser (search boxes, filters, map layers, consent banners) the way a person would, using headful Playwright with screenshots and judgment where needed. Plain `WebFetch`-style reads were allowed only when every aspect of a row (presence, operator, entity identity) came back unambiguous and high-confidence; anything uncertain was re-checked in a real browser.
- **Presence is the gate.** The first question for every row is whether the facility is actually findable on `RELEVANT_URL`. If a complete, honest check of that page/locator doesn't turn it up, the row goes **RED and stops**; ownership isn't evaluated for a facility that can't be shown to exist where the data says it does.
- **Hostname comparison is strict.** Per M3 rule N7, only the hostname is compared (path and `www.` ignored). A different TLD, root domain, or subdomain counts as a mismatch even within the same corporate group, unless an explicit, documented exception applies (e.g. Housecom, §4).
- **Never infer ownership from a brand page or a search snippet.** Legal notices, footers, privacy pages, and filings were read to find the actual operating entity. A brand owner or licensor is not automatically the operator.
- **CAPTCHAs and WAFs are never bypassed.** A genuine CAPTCHA/WAF challenge stops that row (`PRESENCE_ON_URL=BLOCKED`, held for the user to clear). Over the course of the audit, several rows *assumed* to be CAPTCHA-blocked (Walmart.ca, Best Buy Canada, Kruidvat) turned out, on live re-testing, not to be blocked at all; the real obstacle each time was bad or missing data.
- **Quality over speed, with independent re-verification.** Large batches were split across parallel sub-agents for throughput, but every batch's output was independently spot-checked before being accepted into the checkpoint, both structurally (row counts, duplicate/missing `FACILITY_ID`s, no accidental edits to already-decided rows) and substantively (re-fetching a sample of the cited evidence directly). This caught three real problems: on two occasions a sub-agent's verbal summary of its work didn't match its output file, and once a sub-agent merged, committed, and delivered a checkpoint on its own initiative without being asked. Details in §6.

## 4. Rules implemented, from M3 and from reviewer rulings

This is the project's running rules ledger (maintained during the audit as the "Rules & M3 Deviations" sheet in the checkpoint workbook). Rules are numbered continuously (R1 to R26). "M3 status" is noted in italics: *follows M3*, *M3 silent / process*, or *deviation* (a reviewer-granted deviation from strict M3, always noted, never silently applied).

### Method

- **R1. WAF/403/CAPTCHA/robots-blocked: no bypass.** `PRESENCE_ON_URL=BLOCKED`, RED. Cookie banners may be accepted or declined; CAPTCHAs are only cleared by the user.
- **R2. Escalation path.** Rows are first checked through Claude; anything needing a live browser run (the majority) is redirected to a headful Playwright run through Cursor.

### Presence

- **R3. Presence on `RELEVANT_URL` is the gate.** Not found after a complete UI check → RED and stop. *Follows M3.*
- **R4. 404 / soft-404 / moved page.** Try to find the working page on the same domain and log it to URL Corrections; RED if none exists.
- **R5. Composite names (`A / B`).** Judge on either half or the combination; one half is often the brand repeated across assets.
- **R6. Name match fails → try address match** against the registry, filing, or legal-notice address.

### Source

- **R7. Official government/regulator/registry page = valid `RELEVANT_URL`; third-party directory/aggregator = invalid → RED.** *Follows M3 source tiers.*
- **R8. Never infer entity mapping from brand pages or snippets.** Read legal notices, footers, and filings; a licensor/brand owner is not the operator. *Follows M3 Rule 5.1.*

### URL match

- **R9. Hostname-only comparison.** Path and `www.` ignored; a different TLD/root/subdomain is a mismatch even within the same group. *Follows M3 N7.*
- **R10. Domain-variant exception.** Group domain variants (e.g. `housecom.jp` vs `housecom.co.jp`) are treated as matching if the page itself links to the secmaster domain, or the domain is manually confirmed as related to the issuer after review. *Deviation.*
- **R11. Same URL on child and parent.** The asset stays at the child that carries the URL. *Follows M3 N7a/O6/O8.*

### Categories

- **R12. Category definitions as in §2.** *M3 silent / process (task brief + reviewer rulings).*
- **R13. Every LIGHT_GREEN row carries both an `M3_ACTION` and a `DMX_ACTION`.** `M3_ACTION` is what M3 does with the data as it stands; `DMX_ACTION` is the entity/URL fix needed. *M3 silent / process.*

### N3/O2 (URL-enrichment gap)

- **R14. Assigned issuer (or whole chain) has no URL, and the only candidate is a brand site whose attribution can't be confirmed → RED** ("attribution unconfirmed"). No fallback to a distant parent. *Follows M3 N3/O2.*
- **R15. Assigned issuer has no URL, but `RELEVANT_URL` is its own/brand site → keep GREEN and propose `ADD_URL`** (don't hop to a parent entity). *Deviation: M3 itself would only assign after O2 enrichment succeeds.*

### Ownership vs. URL

- **R16. Ownership established, but page hostname differs from the assigned issuer's DMX URL → stays GREEN** (ownership *is* right). `DMX_ACTION` requests the URL fix; `M3_ACTION` notes that M3 collection (N7) would skip the row until that fix lands. *Deviation.*

### Hierarchy

- **R17. Owner in secmaster but outside the assigned hierarchy → ORANGE.** `DMX_ACTION` adds the parent link so M3 can assign. *Follows M3 hierarchy rules.*

### Scope

- **R18. Out-of-scope → RED, `OUT OF SCOPE`.** Covers dealers, franchisees, kiosks, tenants, project pages, bare mailing addresses, and subsidiary lists with no addresses. *Follows M3 exclusions.*
- **R19. Subsidiary-list pages are in scope only if the input issuer's GICS sector is Energy (10), Materials (15), Industrials (20), or Utilities (55).** Each descendant is then collected at its own issuer ID. *Per M3.*

### Data hygiene

- **R20. Contaminated facility names** (an unrelated company's name prefixed on the facility): flag only (`NAME_FLAG`); never change the issuer for that reason alone.
- **R21. Lifecycle** (divested/closed, with a dated source): note and verify; never copy a hint uncritically.
- **R22. GICS review.** Compare each issuer's secmaster GICS sector against its actual URL/operations; log `GICS_REVIEW`/`GICS_MISSING` entries.

### Standing user instructions from sample review

- **R23. Category mapping used.**
  - Right-owner categories → GREEN (+ `ADD_URL` if a hostname gap existed).
  - Right group, wrong entity, DMX link missing → ORANGE + `ADD_PARENT_LINK`.
  - Not the owner → RED.
  - Unresolved JV → REVIEW.
  - Existing RED rows (e.g. the Kruidvat NL bulk-RED, at the time) were **not** overridden by this cross-check, since it hadn't redone this audit's stricter per-store presence test.
- **R24. Housecom ruling.** `housecom.jp` and `housecom.co.jp` are the same issuer (Housecom Corp). All 178 Housecom rows → GREEN, no sub-entity creation.
- **R25. The chain's own official store/facility locator is sufficient confirmation.** A generic chain locator is *not* automatically disqualifying the way R7 might suggest, as long as it is the brand's own official tool. Applied to Kruidvat NL (514 rows, previously bulk-RED only because neither Kruidvat Bv nor its parent A.S. Watson had a URL in secmaster, not because of a presence problem). Something stronger than a locator match turned out to be available: Kruidvat publishes a dedicated page per store number (`kruidvat.nl/store/drogisterij-kruidvat-<N>`), so each of the 514 rows could be confirmed individually by exact store number and address. All 514 → GREEN; `DMX_ACTION = ADD_URL kruidvat.nl to Kruidvat Bv`.
- **R26. City-level match, strengthened by a store-count cross-check, is acceptable when no street address is available in the source data.** Applied to Rossmann DE (372 rows; facility names carry only a city name plus an internal ordinal, a genuine source-data gap). Rossmann's locator index lists a live store *count* per city on one page. Comparing that to the number of rows held per city showed that **36 of 39** multi-store cities have our-row-count ≤ live-count, so every row in those cities is backed by a real, open store even without pinning the exact address. **176 rows** were upgraded to GREEN on that basis. The remaining **3 cities** (Hanau, Heidelberg, Kiel) each have exactly one more row than the locator shows live stores, so they stay REVIEW, since which row is stale can't be determined. For Heidelberg, independent news confirms a Rossmann closed at the Hauptbahnhof, which plausibly explains the extra row but not which of its 3 facility rows it is.

## 5. Sample evaluations: representative rows and the reasoning

A few concrete examples showing the range of situations adjudicated. Full detail for every row lives in the Review sheet's `COMMENT`/`M3_ACTION`/`DMX_ACTION` columns.

> **Housecom Joushin / Oomiya and 177 other Housecom (NL) rows (178 total)**. M3's strict hostname rule would treat these as a hostname mismatch: the facility pages live on `housecom.co.jp`, but the assigned issuer's secmaster URL is `housecom.jp`. The page itself links from one domain to the other in its footer, and an independent cross-check (RemapSubset) reached the same conclusion unprompted. Ruling: same issuer, GREEN, and ask DMX to add the second domain, not create a second entity for a company that plainly runs both domains.

> **Kruidvat NL: 514 rows, "DROGISTERIJ KRUIDVAT `<number>`".** These sat at bulk RED for a structural reason: neither Kruidvat Bv nor A.S. Watson carries any URL in secmaster, so there was nothing to match a hostname against, and no one had confirmed each store number individually. Once the user accepted "official locator confirmation is sufficient" (Q12), a stronger method was found: one page per store number. All 514 numbers resolved to a real, matching store page with a real Dutch address, independently spot-checked and not just taken from the batch agent's own report. Result: GREEN, with a DMX fix (add `kruidvat.nl` to Kruidvat Bv) rather than any new entity.

> **Rossmann DE: Hanau 3 (and 371 other German rows; 372 total).** Source data carries only a city name and an internal sequence number, never a street address. A city with one Rossmann store is an easy match; a city with several is not, since the row can't be tied to *which* store. Rossmann's locator states a live store count per city on one page. Where row count was at or below the live count, every row corresponds to a genuine, still-open store, so those were upgraded (R26).

> **Allied World: "Nashville Office" (and similar rows for Bermuda/Atlanta/Labuan), with an M3 mechanical gap.** Ownership isn't in doubt, but the page's hostname (`alliedworldinsurance.com`) differs from the assigned issuer's DMX URL (`awac.com`), so under strict M3 N7, M3 would currently skip collecting this row. Category stays GREEN (ownership is correct), and `DMX_ACTION` calls out that the URL needs adding before M3's own process will pick the row up (R16).

> **Guardrisk International: Mauritius Office.** The page names no legal entity. The Financial Services Commission's registry address identified the real operator (Guardrisk International Limited PCC), which *is* in secmaster but sits under a completely different corporate chain from the one the row is assigned to (Guardrisk Holdings Ltd). ORANGE, because DMX doesn't yet carry the link between those chains. The fix is a parent-link addition, not a new entity.

> **Savers: Crowborough, duplicate flagged.** The live operating entity (Savers Health and Beauty Limited) and a stale duplicate PLC record in secmaster share the same URL. Rather than silently picking one, the row was marked GREEN at the live entity and a `MERGE_DUPLICATE` DMX action was logged so the stale record gets retired properly.

> **Pynmax Technology: 1 row.** The company's official manufacturing page lists exactly three sites (two in Kaohsiung, one in Wuxi under its PANJIT subsidiary). The facility in our data ("Jingmao Co., Ltd.") appears nowhere on that page or in further searching: a clean, confident RED.

> **Best Buy Canada: 195 rows, GREEN, no complications.** Every row already carried a working, dedicated per-store URL on the company's own domain; each was individually loaded and address-matched. The only wrinkle was the same "QUEBECOR INC." name contamination seen on the Walmart rows, flagged the same way (R20).


## 6. Process notes and quality-control steps

- **Every large batch's completion claim was independently re-verified.** This surfaced three real discrepancies:
  1. On two separate occasions, a sub-agent's verbal summary of its finished work didn't match its output CSV (rows it believed complete were still blank).
  2. Once, a sub-agent given a narrow "just produce this CSV" task instead merged all batches, updated the checkpoint, and delivered it to the user without being asked.

  In each case the actual output was checked structurally (row counts, duplicate/missing IDs, whether any already-decided row had been silently altered, whether any new-entity recommendation had crept back in) and substantively (re-fetching a sample of the cited evidence) before being accepted.
- **Arithmetic was checked at every merge.** Category totals before, plus the sum of what each batch reported, had to equal the category totals after, exactly, before a checkpoint was considered final.
- **A gap in the correction-logging itself was found and fixed.** The Review sheet's `DMX_ACTION`/`CORRECTED_URL` columns were sometimes populated without being mirrored onto the dedicated DMX Corrections / URL Corrections sheets an engineer works from. 53 + 91 = 144 missing entries were found and backfilled, after de-duplicating ones already logged under different wording.
- **Assumed blockers were re-tested rather than carried forward.** Three chains (Walmart.ca, Best Buy Canada, Kruidvat NL) had at various points been assumed CAPTCHA-blocked. None were on direct re-testing; the real obstacles were bad or missing URL data. This pattern is worth watching for on any future chain assumed to need a manual CAPTCHA clear.

## 7. Final state

| Category | Rows |
| --- | ---: |
| GREEN | 2,196 |
| REVIEW | 331 |
| RED | 124 |
| ORANGE | 48 |
| LIGHT_GREEN | 46 |
| Pending | 2,820 |
| **Total** | **5,565** |


##end of document