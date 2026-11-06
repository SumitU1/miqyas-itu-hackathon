# KB v1 coverage check

Generated 2026-10-28 19:08 UTC by `kb/coverage.py`. Source of truth: `sources/sources.json`. Build: `20261026T1648Z`.

**Headline:** 23 of 27 listed sources are in the KB (689 chunks, 164,090 words). 4 are listed but NOT ingested (they need a person to download a file, see below). 2 ingested sources are partial. Nothing here has been checked by a lawyer or a clinician.

## 1. Coverage of the plan's required document families

| Required by the plan | Sources | In KB | Verdict |
|---|---|---|---|
| DHA rules (Dubai health regulator) | DHA-AI-2021, DHA-TELEHEALTH-STD-V4, DHA-TELEHEALTH-POL-2021, DHA-HIS-2024, DHA-MEDAD-2022 | 5 of 5 | covered |
| MOHAP rules (federal health ministry) | MOHAP-MD51-2021, MOHAP-HEALTHAD-GUIDE, MOHAP-PROMO-CODE-2017 | 3 of 3 | covered, but at least one source is partial |
| DoH rules (Abu Dhabi health regulator) | DOH-AI-2018, DOH-HIE-2020, DOH-ADHICS-V2 | 3 of 3 | covered |
| TDRA device rules | TDRA-TAR-POLICY-V3, TDRA-TAR-REG-V3, TDRA-IOT-PROC-V1 | 3 of 3 | covered |
| PDPL (personal data protection law) | UAE-PDPL-2021 | 1 of 1 | covered, but at least one source is partial |
| Federal Law 2/2019 on ICT in health (+ executive regulations) | UAE-FL2-2019, UAE-CR32-2020 | 2 of 2 | covered |
| Medical-product decree (Federal Decree-Law 38/2024) | UAE-FDL38-2024 | 0 of 1 | NOT covered |
| Advertising rules | NMC-AD-GUIDE, DHA-MEDAD-2022, MOHAP-HEALTHAD-GUIDE, UAE-FL15-2020 | 3 of 4 | partly covered |
| AI-ethics and AI policy | UAE-AI-CHARTER-2024, UAE-AI-STRATEGY-2031, DUBAI-AI-ETHICS-2022, DHA-AI-2021, DOH-AI-2018 | 5 of 5 | covered |
| Standards: ITU-T Y.3172 and AI Readiness Framework 2.0 | ITU-Y3172, ITU-AIREADY-2 | 2 of 2 | covered |
| Extra (not in the plan): medical liability, global health-AI ethics | UAE-FDL4-2016, WHO-AI-HEALTH-2021 | 0 of 2 | NOT covered |

## 2. Per-source status

| Source | Kind | Level | In KB | Chunks | Words | PDF pages covered | No-text pages | Fetch | Currency note |
|---|---|---|---|---|---|---|---|---|---|
| ITU-Y3172 | standard | international | yes | 46 | 11555 | 34 | 3 | http | in force |
| ITU-AIREADY-2 | standard | international | yes | 76 | 19279 | 55 | - | http | current |
| UAE-FL2-2019 | law | federal | yes | 34 | 2697 | 12 of 12 | - | http | in force |
| UAE-CR32-2020 | regulation | federal | yes | 16 | 2303 | 12 of 12 | 2 | http | in force (effective 2020-10-30 per the legislation portal) |
| MOHAP-MD51-2021 | regulation | federal | yes (partial) | 1 | 170 | - | - | browser | in force; THIS ENTRY IS THE MINISTRY'S SUMMARY, not the full text (full text is an Arabic PDF) |
| UAE-PDPL-2021 | law | federal | yes (partial) | 18 | 3149 | - | - | browser | in force from 2022-01-02. Executive Regulations: status NOT confirmed by this project |
| DHA-AI-2021 | policy | dubai | yes | 13 | 3267 | 17 | - | http | issued 2021-07-01, effective 2021-10-01; stated revision date 2026-07-01 has PASSED: check for a newer version |
| DOH-AI-2018 | policy | abu-dhabi | yes | 11 | 2597 | 11 | - | http | version 0.9, April 2018; not confirmed whether replaced |
| DHA-TELEHEALTH-POL-2021 | policy | dubai | yes | 5 | 1164 | 5 | - | http | issued 2021-08-16; stated revision date 2026-08-16 has PASSED: check for a newer version |
| DHA-TELEHEALTH-STD-V4 | standard | dubai | yes | 76 | 19256 | 94 | - | http | Version 4, issued 2025-09-26, effective 2025-11-26 |
| DHA-HIS-2024 | policy | dubai | yes | 36 | 9017 | 39 | - | http | issued 2024-08-10, effective 2024-11-10 |
| DOH-HIE-2020 | policy | abu-dhabi | yes | 55 | 14056 | 44 | - | http | effective 2020-04-16; not confirmed whether replaced |
| DOH-ADHICS-V2 | standard | abu-dhabi | yes | 116 | 29588 | 137 | 1 | http | V2, published May 2024, effective August 2024 |
| DHA-MEDAD-2022 | standard | dubai | yes | 24 | 5921 | 28 | - | http | v1.1, issued 2022-08-03, effective 2022-10-03 |
| MOHAP-HEALTHAD-GUIDE | guideline | federal | yes | 4 | 840 | 4 | - | http | date not stated in the document; check currency |
| MOHAP-PROMO-CODE-2017 | guideline | federal | yes | 22 | 5579 | 15 | - | http | Nov 2017; may predate Federal Decree-Law 38/2024 |
| NMC-AD-GUIDE | guideline | federal | yes | 12 | 3005 | 17 | - | http | pre-2023 guide: may be superseded by the current media law and executive regulations; check currency |
| TDRA-TAR-POLICY-V3 | policy | federal | yes | 9 | 2101 | 9 | - | http | Version 3.0, issued 2022-05-09 |
| TDRA-TAR-REG-V3 | regulation | federal | yes | 25 | 5717 | 22 | - | http | Version 3.0, issued 2022-05-09 |
| TDRA-IOT-PROC-V1 | regulation | federal | yes | 6 | 1498 | 8 | - | http | Version 1; the companion IoT Regulatory Policy (English) was NOT located as a primary document |
| UAE-AI-CHARTER-2024 | strategy | federal | yes | 3 | 649 | 6 | - | http | current; non-binding guidance |
| UAE-AI-STRATEGY-2031 | strategy | federal | yes | 44 | 11250 | 23 | 2 | http | current strategy document |
| DUBAI-AI-ETHICS-2022 | guideline | dubai | yes | 37 | 9432 | 24 | 1 | http | Dec 2022 edition; non-binding |
| UAE-FDL38-2024 | law | federal | NO | 0 | 0 | - | - | manual-pending | in force from 2025-01-02 with a one-year grace period (per law-firm summaries; not verified against the text) |
| UAE-FL15-2020 | law | federal | NO | 0 | 0 | - | - | manual-pending | in force; amended by Federal Decree-Law 5/2023 (per secondary summaries, unverified) |
| UAE-FDL4-2016 | law | federal | NO | 0 | 0 | - | - | manual-pending | in force; executive regulations are Cabinet Resolution 40/2019 (per secondary summaries, unverified) |
| WHO-AI-HEALTH-2021 | guideline | international | NO | 0 | 0 | - | - | manual-pending | 2021 guidance |

## 3. Listed but not ingested (what Sumit or a teammate has to do)

- **UAE-FDL38-2024**: uaelegislation.gov.ae holds the bot check on scripts and on the built-in browser; the PDF is at https://uaelegislation.gov.ae/en/legislations/2751/download. Save it by hand as kb/raw/UAE-FDL38-2024.pdf.
- **UAE-FL15-2020**: Same bot protection. PDF at https://uaelegislation.gov.ae/en/legislations/1455/download. Save by hand as kb/raw/UAE-FL15-2020.pdf.
- **UAE-FDL4-2016**: Same bot protection. PDF at https://uaelegislation.gov.ae/en/legislations/1192/download. Save by hand as kb/raw/UAE-FDL4-2016.pdf.
- **WHO-AI-HEALTH-2021**: The WHO IRIS download returned a bot-protection page to scripts. Download the PDF by hand from the WHO page and save as kb/raw/WHO-AI-HEALTH-2021.pdf. Licence is CC BY-NC-SA 3.0 IGO per the WHO page summary found in search (verify on the WHO page).

## 4. Integrity checks (automatic)

| Check | Result | Detail |
|---|---|---|
| every chunk carries all citation fields | PASS | 689 chunks checked |
| chunk ids are unique | PASS |  |
| every chunk points to a registered source | PASS |  |
| chunk text hashes recompute | PASS |  |
| raw files match the download manifest | PASS |  |
| public export is excerpt-only for excerpt sources (<= 60 words + marker) | PASS |  |
| no source is marked 'full' redistribution without a licence review | PASS | all sources are excerpt-only |
| every ingested source has a canonical URL | PASS |  |
| all chunks marked not-legally-reviewed | PASS |  |
| clinical-content sources labelled clinical-unreviewed | PASS |  |

## 5. Known limitations of KB v1

- **Not legally reviewed.** No UAE lawyer has checked any chunk or any mapping. Clinical material is labelled `clinical-unreviewed`; no clinician (including Dr. Neeta) has signed off on anything here.
- **Translations.** English versions only. Where the portal says the Arabic text prevails, the Arabic text is the binding one.
- **Partial PDPL.** Only articles 1, 2, 4, 5, 6, 9, 13, 17, 18, 20-23 are in the KB. The Executive Regulations are not in the KB and their status is not confirmed here.
- **Decision 51/2021 is the ministry's summary, not the resolution.** The binding Arabic text is a MOHAP PDF.
- **Federal Law 2/2019 and its Executive Regulations come from the Abu Dhabi DoH compilation (Book 10).** The compilation is 'all rights reserved'; replace it with the legislation-portal text and keep the same chunk ids.
- **Possible staleness.** Several policies show a revision date that has already passed (DHA AI policy: 2026-07-01; DHA Telehealth Policy: 2026-08-16) or are old drafts (DoH AI policy v0.9, 2018; NMC advertising guide predates the current media law). The KB records the version note per chunk; it does not know whether a newer version exists.
- **Scanned pages.** Pages with no text layer are not in the KB (counts in section 2).
- **Retrieval is lexical (BM25).** It can miss answers that need a second hop, for example the penalty clause (Art. 24) for the localisation rule (Art. 13). See RETRIEVAL_TESTS.md.
- **Pipeline mapping (nodes, dimensions) is the analyst's own and unreviewed.**
