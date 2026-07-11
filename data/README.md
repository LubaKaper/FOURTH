# data/

All CSVs and PDFs Fourth depends on. Files are committed to the repo so a fresh clone can run the full pipeline without re-downloading anything.

All sources are public domain (CMS, CDC, KFF, NCHS) or open-access peer-reviewed (Cureus, CC-BY 4.0).

## File Inventory

| Local filename | Source | Downloaded | Refresh cadence |
|---|---|---|---|
| `Birthing_Friendly_Hospitals_Geocoded.csv` | CMS Provider Data Catalog | April 2026 | Annual |
| `HCAHPS-Hospital-NY.csv` | CMS Provider Data Catalog (NY-filtered via `scripts/filter_hcahps_to_ny.py`) | April 2026 | Quarterly |
| `Maternal_Health-Hospital.csv` | CMS Provider Data Catalog | May 2026 | Quarterly |
| `FY_2026_Hospital_Readmissions_Reduction_Program_Hospital.csv` | CMS Provider Data Catalog | May 2026 | Annual |
| `core-set-ppc-ad-ny.csv` | CMS Medicaid Core Set Data Dashboard (PPC-AD, NY filter) | April 2026 | Annual |
| `core-set-ppc-ch-ny.csv` | CMS Medicaid Core Set Data Dashboard (PPC-CH timeliness, NY filter) | April 2026 | Annual |
| `core-set-ppc2-ad-ny.csv` | CMS Medicaid Core Set Data Dashboard (PPC2-AD age 21+, NY filter) | April 2026 | Annual |
| `core-set-ppc2-ch-ny.csv` | CMS Medicaid Core Set Data Dashboard (PPC2-CH under 21, NY filter) | April 2026 | Annual |
| `core-set-ccp-ch-ny.csv` | CMS Medicaid Core Set Data Dashboard (CCP-CH contraceptive, NY filter) | April 2026 | Annual |
| `kff_postpartum_coverage.csv` | KFF Medicaid Postpartum Coverage Extension Tracker | April 2026 | As policy changes |
| `nnpqc_funding.csv` | National Network of Perinatal Quality Collaboratives | April 2026 | As funding changes |
| `hestat113.pdf` | NCHS Health E-Stat 113 (Maternal Mortality 2024) | March 2026 release | Annual (March release) |
| `cureus-racial-disparity.pdf` | Kamijo et al., Cureus 17(8):e90416, 2025 | August 2025 | Static, citation only |

## Source URLs

For refreshing files when they get out of date.

### CMS

- **Birthing-Friendly registry:** https://data.cms.gov/provider-data/dataset/hbf-map
- **HCAHPS-Hospital (full national file):** https://data.cms.gov/provider-data/dataset/dgck-syfz
  - After download, run `python scripts/filter_hcahps_to_ny.py` to produce the NY-only file. Do not commit the full national file (~102 MB).
- **Maternal Health - Hospital:** https://data.cms.gov/provider-data/dataset/nrdb-3fcy
- **Hospital Readmissions Reduction Program:** https://data.cms.gov/provider-data/topics/hospitals/hospital-readmissions
- **Medicaid Core Set Data Dashboard:** https://www.medicaid.gov/medicaid/quality-of-care/core-set-data-dashboard/welcome
  - Pick measure (PPC-AD, PPC-CH, PPC2-AD, PPC2-CH, or CCP-CH), filter to NY, export CSV

### KFF

- **Postpartum Medicaid Coverage Tracker:** https://www.kff.org/medicaid/issue-brief/medicaid-postpartum-coverage-extension-tracker/

### NNPQC

- **State PQC funding:** https://nnpqc.org/

### NCHS

- **Health E-Stat 113 / maternal mortality source:** needs re-verification before citation. The previously listed `https://www.cdc.gov/nchs/products/databriefs/db113.htm` URL resolves to an unrelated data brief and should not be used as the maternal mortality source.

### Cureus

- **Racial disparity paper:** https://www.cureus.com/articles/396068-racial-disparities-in-maternal-mortality

## Refresh Process

If a file goes stale:

1. Download the new version from the source URL above
2. Rename to match the filename in this README (CMS filenames in the wild are ugly; we rename for code readability)
3. For HCAHPS specifically: drop the full national file in `data/`, run `python scripts/filter_hcahps_to_ny.py`, then delete the full file
4. Open the file and confirm column headers haven't changed. If they have, update `src/commitment_ingester.py` and `src/outcome_scorer.py` to match
5. Run the full test suite: `.venv\Scripts\python -m pytest tests/ -v`
6. Update the "Downloaded" date in the table above
7. Commit with message: `chore(data): refresh [filename] from [source] [YYYY-MM-DD]`

## What's NOT in here

These are referenced in PRD as v2 expansion sources but not committed in v1:

- CMS Hospital Provider Cost Report (Medicaid payer mix)
- CMS Medicaid Core Set: PCR-AD, PDS-AD, LRCD-AD
- CDC WONDER state-level mortality exports
- Full national HCAHPS-Hospital.csv (NY-filtered version is in v1)

If you're building toward v2, download these from the URLs in PRD's "v2 expansion sources" section and add to this folder with a corresponding row above.

## Notes on Specific Files

### Birthing_Friendly_Hospitals_Geocoded.csv

2,265 rows nationally, 101 NY. Fields: name, addr, city, state, zip, lat, lon. **Has no CCN.** Tool 1 joins this to `HCAHPS-Hospital-NY.csv` by name (with normalization for the 6 NY hospitals whose names don't exactly match) to recover the CCN.

### HCAHPS-Hospital-NY.csv

NY-only filtered version. 161 facilities, ~10,900 measure rows, ~3.3 MB. Filtered from the full 102 MB CMS export using `scripts/filter_hcahps_to_ny.py`. Tool 2 reads three measures: `H_COMP_6_STAR_RATING`, `H_STAR_RATING`, `H_DISCH_HELP_Y_P`.

### Maternal_Health-Hospital.csv

National CMS Maternal Health file. Tool 2 reads `PC_07a` from `Score` for severe obstetric complications when reported, and `SM_7` from `Score` for maternal morbidity structural measure participation.

### FY_2026_Hospital_Readmissions_Reduction_Program_Hospital.csv

National CMS HRRP file. Tool 2 reads `Excess Readmission Ratio`; `readmission_penalty` is true when any reported ratio for the hospital is above 1.0.

### core-set-ppc-ad-ny.csv

The "core-set-data-dashboard" exports come with a multi-row preamble (Title, Timeframe, etc.) before the actual CSV header. Tool 2 skips these preamble rows when parsing. NY 2023 rate = 82.4%. **Primary state benchmark for the within-state mismatch story.**

### Other core-set-*.csv files

`core-set-ppc-ch-ny.csv`, `core-set-ppc2-ad-ny.csv`, `core-set-ppc2-ch-ny.csv`, `core-set-ccp-ch-ny.csv`. Same preamble format as PPC-AD. **Supporting context only** — displayed in the briefing card sidebar to show NY is top quartile across the board, but not used in scoring math.

### kff_postpartum_coverage.csv

Has a 2-row preamble like the CMS Core Set files. Tool 4 reads the "12-month extension implemented" status for the hospital's state. NY = implemented June 2023. Drives the `medicaid_extended` field and the financial email variant.

### nnpqc_funding.csv

State-level perinatal quality collaborative funding status. NY = funded. Used as supporting context in the briefing card.

### hestat113.pdf and cureus-racial-disparity.pdf

Citation only. Not parsed by any tool. The dashboard cites these; values are extracted manually into `src/constants.py` if needed (e.g., racial disparity ratios for `racial_disparity_flag` calculation).
