# Retrieval test results (KB v1)

Run: 2026-10-26 16:48 UTC. Cases: `kb/tests/retrieval_cases.json` (written before the first run). Method: BM25, top 5, offline, no model.

## Summary

| | Full local KB | Public excerpt export |
|---|---|---|
| Positive cases | 48 | 48 |
| Hit@1 | 40 | 41 |
| Hit@3 | 44 | 44 |
| Hit@5 | 45 | 45 |
| MRR@5 | 0.873 | 0.886 |
| Off-topic cases NOT given strong evidence (pass) | 15 / 15 | 15 / 15 |
| ...of which evidence = none / weak / strong | 11 / 4 / 0 | 12 / 3 / 0 |
| On-topic cases rated strong / weak / none | 23 / 25 / 0 | 11 / 37 / 0 |
| Known-gap cases (documents still manual-pending) | 3 | 3 |

## Held-out cases (written after the tuning, never used to tune)

Full KB: positives 9, hit@5 9, hit@1 8, MRR@5 0.917; off-topic not given strong evidence 6 of 6.
Public export: positives 9, hit@5 9; off-topic not given strong evidence 6 of 6.

The public export keeps only a 60-word excerpt per chunk, so the `must_contain` phrase check is applied to the full KB only.
Known-gap cases are expected to miss: they point at documents not yet in the KB (see KB_COVERAGE.md). They are listed so the gap is visible, not hidden.

## Run history (every run is kept, including the baseline before any tuning)

| run | label | cases | full hit@1 / @3 / @5 | full MRR@5 | full negatives abstained | public hit@5 | public negatives abstained |
|---|---|---|---|---|---|---|---|
| 1 | baseline: BM25, no synonyms, coverage thresholds 0.70/0.45 (30 positive + 3 negative written first, then 9 positive + 6 negative added blind) | 51 | 32 / 35 / 36 of 39 | 0.861 | 2 of 9 | 36 of 39 | 2 of 9 |
| 2 | run 2: + synonym expansion, spelling normalisation, evidence rule v2 (score-based). Tuned post hoc on the 48 cases of run 1 | 51 | 32 / 36 / 36 of 39 | 0.863 | 9 of 9 | 36 of 39 | 9 of 9 |
| 3 | run 3: same code as run 2 + 15 held-out cases (9 positive, 6 negative) written after tuning | 66 | 40 / 44 / 45 of 48 | 0.873 | 15 of 15 | 45 of 48 | 15 of 15 |
| 4 | run 4: after citation fixes (Art. 22/23 headings, tail-merge only within a section); same retrieval code as run 2 | 66 | 40 / 44 / 45 of 48 | 0.873 | 15 of 15 | 45 of 48 | 15 of 15 |
| 5 | run 5: clean rebuild from kb/raw (reproducibility check) | 66 | 40 / 44 / 45 of 48 | 0.873 | 15 of 15 | 45 of 48 | 15 of 15 |

## Full local KB (latest run)

| id | kind | rank | evidence | pass | top result |
|---|---|---|---|---|---|
| S1-01 | positive | 3 | weak | yes | [DHA-TELEHEALTH-STD-V4] §10.5 Consent is not required for:, PDF pp.42-44 (14.357) |
| S1-02 | positive | 1 | weak | yes | [DHA-AI-2021] §3 Definitions/Abbreviations:, PDF pp.6-7 (12.804) |
| S1-03 | positive | 1 | strong | yes | [UAE-PDPL-2021] Art. 18 Right to Processing and Automated Processing (32.91) |
| S1-04 | positive | 1 | weak | yes | [DOH-AI-2018] §8 Enforcement, Compliance and Sanctions, PDF pp.10-11 (14.904) |
| S1-05 | positive | 1 | strong | yes | [UAE-PDPL-2021] Art. 21 Assessment of the Impact of Personal Data Protection (17.257) |
| S2-01 | positive | 2 | strong | yes | [MOHAP-MD51-2021] official MOHAP brief (summary, no article numbers) (20.643) |
| S2-02 | positive | 1 | weak | yes | [MOHAP-MD51-2021] official MOHAP brief (summary, no article numbers) (21.608) |
| S2-03 | positive | - | weak | NO | [MOHAP-MD51-2021] official MOHAP brief (summary, no article numbers) (22.146) |
| S2-04 | positive | 1 | weak | yes | [TDRA-TAR-REG-V3] Table Of Contents, PDF pp.2-4 (19.11) |
| S2-05 | positive | 1 | strong | yes | [UAE-PDPL-2021] Art. 2 Scope of Application of the Decree by Law (21.606) |
| S2-06 | positive | 1 | strong | yes | [UAE-PDPL-2021] Art. 23 Cross-Border Transfer and Sharing of Personal Data for Processing Purposes if a Pr (28.857) |
| S2-07 | positive | 2 | weak | yes | [DHA-TELEHEALTH-STD-V4] §17.12 Teleprescribing (Physician Only), PDF pp.67-69 (11.462) |
| S2-08 | positive | 1 | weak | yes | [TDRA-IOT-PROC-V1] PDF pp.1-3 (23.285) |
| S3-01 | positive | 1 | weak | yes | [DOH-HIE-2020] §4.3.13 All Healthcare Facilities shall:, PDF pp.27-28 (19.302) |
| S3-02 | positive | 1 | strong | yes | [DOH-HIE-2020] §4.2.1 DOH shall:, PDF pp.20-21 (22.033) |
| S3-03 | positive | 1 | weak | yes | [DHA-TELEHEALTH-STD-V4] §6.6.3 Explicit patient consent must be secured before commencing telehealth, PDF pp.26-27 (18.749) |
| S3-04 | positive | 1 | strong | yes | [DOH-ADHICS-V2] PDF pp.1-3 (18.84) |
| S3-05 | positive | 1 | weak | yes | [UAE-CR32-2020] Art. 4, PDF p.29 (14.677) |
| S3-06 | positive | 1 | weak | yes | [DHA-HIS-2024] §4.4.2 Ad-hoc information sharing:, PDF pp.16-17 (18.974) |
| S4-01 | positive | 1 | strong | yes | [MOHAP-HEALTHAD-GUIDE] PDF pp.1-3 (27.983) |
| S4-02 | positive | 1 | weak | yes | [NMC-AD-GUIDE] §4 Any person trading advertising content, including from the one that is, PDF pp.8-10 (22.018) |
| S4-03 | positive | - | weak | NO | [NMC-AD-GUIDE] §4 Any person trading advertising content, including from the one that is, PDF pp.8-10 (16.172) |
| S4-04 | positive | 1 | strong | yes | [MOHAP-PROMO-CODE-2017] PDF pp.3-4 (32.615) |
| S4-05 | positive | 1 | weak | yes | [MOHAP-HEALTHAD-GUIDE] PDF pp.3-4 (25.892) |
| S4-06 | positive | 1 | strong | yes | [UAE-PDPL-2021] Art. 17 Right to Stop Processing (29.343) |
| STD-01 | positive | 1 | strong | yes | [UAE-AI-CHARTER-2024] PDF pp.1-3 (20.47) |
| STD-02 | positive | 1 | strong | yes | [ITU-Y3172] Req-Ml-Mng-005, PDF p.25 (32.068) |
| STD-03 | positive | 1 | strong | yes | [ITU-Y3172] Req-Ml-Mng-005, PDF pp.24-25 (22.363) |
| STD-04 | positive | - | strong | NO | [ITU-AIREADY-2] §3 Structural Approach, PDF pp.30-31 (26.335) |
| STD-05 | positive | 1 | strong | yes | [DUBAI-AI-ETHICS-2022] §3.2.2 Guidelines, PDF p.13 (22.448) |
| B-01 | positive | 1 | strong | yes | [DOH-ADHICS-V2] §2 Definitions and Abbreviations, PDF pp.8-10 (19.989) |
| B-02 | positive | 1 | strong | yes | [DHA-TELEHEALTH-STD-V4] Introduction, PDF pp.5-8 (18.151) |
| B-03 | positive | 1 | weak | yes | [UAE-AI-STRATEGY-2031] Objectives, PDF pp.11-12 (16.832) |
| B-04 | positive | 1 | strong | yes | [UAE-PDPL-2021] Art. 22 Cross-Border Transfer and Sharing of Personal Data for Processing Purposes if a Pr (19.719) |
| B-05 | positive | 1 | weak | yes | [UAE-PDPL-2021] Art. 9 Reporting Personal Data Breach (26.523) |
| B-06 | positive | 1 | weak | yes | [TDRA-TAR-REG-V3] Table Of Contents, PDF pp.9-10 (20.992) |
| B-07 | positive | 1 | strong | yes | [DHA-TELEHEALTH-STD-V4] §6.5 For Travelling UAE Citizens and Residents Holding Emirates ID (EID):, PDF pp.25-26 (15.683) |
| B-08 | positive | 3 | weak | yes | [DUBAI-AI-ETHICS-2022] §3.1.1 Principle, PDF p.10 (12.494) |
| B-09 | positive | 1 | weak | yes | [DUBAI-AI-ETHICS-2022] §9 See IBM WatsonPaths, PDF p.15 (18.652) |
| NEG-04 | negative | - | none | yes | [DOH-HIE-2020] §5.2.2 ADHIE Shall:, PDF pp.35-36 (6.553) |
| NEG-05 | negative | - | none | yes | [UAE-AI-STRATEGY-2031] Industries, PDF p.20 (6.849) |
| NEG-06 | negative | - | none | yes | [DHA-HIS-2024] §4.15 Remote Working (Home, Off-Site, Community etc.), PDF pp.26-27 (6.483) |
| NEG-07 | negative | - | weak | yes | [DHA-TELEHEALTH-STD-V4] §4 Telehealth Triage and Advisory Services:, PDF pp.88-90 (16.724) |
| NEG-08 | negative | - | weak | yes | [UAE-AI-STRATEGY-2031] References, PDF pp.23-24 (10.968) |
| NEG-09 | negative | - | none | yes | [DHA-TELEHEALTH-STD-V4] §14.5.1 Ensure equipment and tools, software and hardware are appropriate for, PDF pp.53-55 (5.293) |
| H-01 | positive | 1 | strong | yes | [ITU-Y3172] Req-Ml-Mng-005, PDF pp.20-21 (26.227) |
| H-02 | positive | 1 | weak | yes | [TDRA-IOT-PROC-V1] Contents, PDF pp.3-5 (31.969) |
| H-03 | positive | 1 | weak | yes | [DOH-AI-2018] §6 Policy Statement, PDF pp.8-9 (20.868) |
| H-04 | positive | 1 | weak | yes | [UAE-FL2-2019] Art. 20, PDF p.23 (17.55) |
| H-05 | positive | 4 | strong | yes | [MOHAP-PROMO-CODE-2017] PDF pp.3-4 (21.002) |
| H-06 | positive | 1 | strong | yes | [MOHAP-HEALTHAD-GUIDE] PDF pp.1-3 (19.766) |
| H-07 | positive | 1 | weak | yes | [UAE-AI-CHARTER-2024] PDF pp.1-3 (19.734) |
| H-08 | positive | 1 | weak | yes | [ITU-AIREADY-2] §3 Structural Approach, PDF pp.22-23 (14.195) |
| H-09 | positive | 1 | strong | yes | [UAE-PDPL-2021] Art. 4 Cases of Processing Personal Data without the Consent of its Owner (26.364) |
| HN-01 | negative | - | none | yes | [UAE-AI-STRATEGY-2031] Ecosystem For Ai, PDF pp.15-16 (7.434) |
| HN-02 | negative | - | none | yes | [ITU-AIREADY-2] §3 Structural Approach, PDF pp.26-27 (6.017) |
| HN-03 | negative | - | weak | yes | [UAE-PDPL-2021] Art. 6 Terms of Consent to Data Processing (10.447) |
| HN-04 | negative | - | none | yes | [UAE-AI-STRATEGY-2031] Objectives, PDF pp.10-11 (8.56) |
| HN-05 | negative | - | weak | yes | [DUBAI-AI-ETHICS-2022] §3 From ISO/IEC 2382:2015, PDF p.7 (10.077) |
| HN-06 | negative | - | none | yes | [MOHAP-HEALTHAD-GUIDE] PDF p.3 (8.309) |
| NEG-01 | negative | - | none | yes | [ITU-AIREADY-2] §3 Structural Approach, PDF pp.27-28 (7.772) |
| NEG-02 | negative | - | none | yes | [UAE-AI-STRATEGY-2031] Jobs Enabled By Ai, PDF pp.17-18 (7.831) |
| NEG-03 | negative | - | none | yes | [UAE-AI-STRATEGY-2031] Ecosystem For Ai, PDF pp.16-17 (6.224) |
| GAP-01 | known_gap | - | weak | NO | [MOHAP-HEALTHAD-GUIDE] PDF pp.3-4 (24.738) |
| GAP-02 | known_gap | - | weak | NO | [UAE-FL2-2019] Art. 24, PDF p.24 (17.314) |
| GAP-03 | known_gap | - | weak | NO | [UAE-CR32-2020] PDF p.27 (11.83) |

## Public excerpt export (latest run)

| id | kind | rank | evidence | pass | top result |
|---|---|---|---|---|---|
| S1-01 | positive | - | weak | NO | [DHA-TELEHEALTH-STD-V4] Definitions, PDF pp.15-17 (11.752) |
| S1-02 | positive | 1 | weak | yes | [DHA-AI-2021] §3 Definitions/Abbreviations:, PDF pp.6-7 (10.353) |
| S1-03 | positive | 1 | weak | yes | [UAE-PDPL-2021] Art. 18 Right to Processing and Automated Processing (30.423) |
| S1-04 | positive | 1 | weak | yes | [DOH-AI-2018] §9 Included but not limited to ADSEC Information Security Standards:, PDF p.11 (12.896) |
| S1-05 | positive | 1 | weak | yes | [UAE-PDPL-2021] Art. 21 Assessment of the Impact of Personal Data Protection (16.487) |
| S2-01 | positive | 1 | strong | yes | [UAE-FL2-2019] Art. 13, PDF p.21 (23.608) |
| S2-02 | positive | 1 | weak | yes | [MOHAP-MD51-2021] official MOHAP brief (summary, no article numbers) (14.673) |
| S2-03 | positive | 2 | weak | yes | [MOHAP-MD51-2021] official MOHAP brief (summary, no article numbers) (27.422) |
| S2-04 | positive | 1 | weak | yes | [TDRA-TAR-POLICY-V3] §7 Essential Requirements, PDF pp.7-8 (19.577) |
| S2-05 | positive | 1 | weak | yes | [UAE-PDPL-2021] Art. 22 Cross-Border Transfer and Sharing of Personal Data for Processing Purposes if a Pr (17.247) |
| S2-06 | positive | 1 | weak | yes | [UAE-PDPL-2021] Art. 22 Cross-Border Transfer and Sharing of Personal Data for Processing Purposes if a Pr (21.014) |
| S2-07 | positive | 2 | weak | yes | [UAE-FL2-2019] Art. 4, PDF p.18 (10.393) |
| S2-08 | positive | 1 | weak | yes | [TDRA-IOT-PROC-V1] Contents, PDF pp.5-6 (18.912) |
| S3-01 | positive | 5 | weak | yes | [DOH-ADHICS-V2] §7 Ensure that employees of the entity and third-party, PDF pp.75-76 (16.309) |
| S3-02 | positive | 1 | weak | yes | [DOH-HIE-2020] §4.2.2.2 Seek patient consent for the sharing of Patient Data via the ADHIE in, PDF pp.21-22 (20.485) |
| S3-03 | positive | 1 | weak | yes | [DHA-TELEHEALTH-STD-V4] §6.6.3 Explicit patient consent must be secured before commencing telehealth, PDF pp.26-27 (15.707) |
| S3-04 | positive | 1 | weak | yes | [DOH-ADHICS-V2] §8 Appendices, PDF pp.132-133 (16.066) |
| S3-05 | positive | 1 | weak | yes | [UAE-FL2-2019] Art. 8, PDF p.19 (13.988) |
| S3-06 | positive | 1 | weak | yes | [DHA-HIS-2024] §4.4.2 Ad-hoc information sharing:, PDF pp.16-17 (19.556) |
| S4-01 | positive | 1 | strong | yes | [MOHAP-HEALTHAD-GUIDE] PDF p.3 (28.373) |
| S4-02 | positive | 1 | weak | yes | [DHA-MEDAD-2022] §2 PURPOSE, PDF pp.11-12 (20.434) |
| S4-03 | positive | - | weak | NO | [DOH-AI-2018] §6 Policy Statement, PDF pp.8-9 (11.933) |
| S4-04 | positive | 1 | weak | yes | [MOHAP-PROMO-CODE-2017] PDF pp.1-3 (17.01) |
| S4-05 | positive | 1 | weak | yes | [MOHAP-HEALTHAD-GUIDE] PDF pp.3-4 (23.948) |
| S4-06 | positive | 1 | strong | yes | [UAE-PDPL-2021] Art. 17 Right to Stop Processing (31.484) |
| STD-01 | positive | 1 | strong | yes | [UAE-AI-CHARTER-2024] PDF pp.1-3 (20.155) |
| STD-02 | positive | 1 | weak | yes | [ITU-Y3172] Req-Ml-Mng-005, PDF p.25 (28.992) |
| STD-03 | positive | 1 | strong | yes | [ITU-Y3172] Req-Ml-Mng-005, PDF pp.21-22 (22.036) |
| STD-04 | positive | 1 | weak | yes | [ITU-AIREADY-2] §3 Structural Approach, PDF pp.30-31 (16.484) |
| STD-05 | positive | 1 | weak | yes | [DUBAI-AI-ETHICS-2022] §3.2.2 Guidelines, PDF p.11 (17.421) |
| B-01 | positive | 1 | strong | yes | [DOH-ADHICS-V2] §6 Decommissioning and/or secure disposal of medical, PDF pp.37-38 (19.549) |
| B-02 | positive | 1 | weak | yes | [DHA-TELEHEALTH-STD-V4] §17.14.2 The pharmacist should monitor the patient’s medication therapy on an, PDF pp.71-72 (12.889) |
| B-03 | positive | 1 | weak | yes | [UAE-AI-STRATEGY-2031] An Ai Destination, PDF p.12 (18.403) |
| B-04 | positive | 1 | weak | yes | [UAE-PDPL-2021] Art. 22 Cross-Border Transfer and Sharing of Personal Data for Processing Purposes if a Pr (20.717) |
| B-05 | positive | 1 | strong | yes | [UAE-PDPL-2021] Art. 9 Reporting Personal Data Breach (27.73) |
| B-06 | positive | 1 | weak | yes | [TDRA-TAR-REG-V3] Table Of Contents, PDF pp.10-11 (20.171) |
| B-07 | positive | 1 | strong | yes | [DHA-TELEHEALTH-STD-V4] §6.6.3 Explicit patient consent must be secured before commencing telehealth, PDF pp.26-27 (15.22) |
| B-08 | positive | - | weak | NO | [DUBAI-AI-ETHICS-2022] §3.2.2 Guidelines, PDF p.11 (13.205) |
| B-09 | positive | 1 | weak | yes | [DUBAI-AI-ETHICS-2022] §3.2.2 Guidelines, PDF p.12 (15.907) |
| NEG-04 | negative | - | none | yes | [DOH-HIE-2020] §5.2.2 ADHIE Shall:, PDF pp.35-36 (6.642) |
| NEG-05 | negative | - | none | yes | [ITU-AIREADY-2] §3 Structural Approach, PDF pp.24-25 (6.299) |
| NEG-06 | negative | - | none | yes | [DHA-HIS-2024] §4.15 Remote Working (Home, Off-Site, Community etc.), PDF pp.26-27 (9.061) |
| NEG-07 | negative | - | weak | yes | [MOHAP-HEALTHAD-GUIDE] PDF pp.3-4 (11.609) |
| NEG-08 | negative | - | weak | yes | [UAE-AI-STRATEGY-2031] References, PDF pp.23-24 (13.116) |
| NEG-09 | negative | - | none | yes | [DHA-TELEHEALTH-STD-V4] §14.5.1 Ensure equipment and tools, software and hardware are appropriate for, PDF pp.53-55 (6.907) |
| H-01 | positive | 1 | strong | yes | [ITU-Y3172] Req-Ml-Mng-005, PDF pp.20-21 (27.75) |
| H-02 | positive | 1 | weak | yes | [TDRA-IOT-PROC-V1] Contents, PDF pp.3-5 (22.06) |
| H-03 | positive | 1 | weak | yes | [DOH-AI-2018] §7.1.2.1 Robust and responsive as evidenced by:, PDF p.9 (22.089) |
| H-04 | positive | 1 | weak | yes | [UAE-FL2-2019] Art. 20, PDF p.23 (20.047) |
| H-05 | positive | 3 | strong | yes | [MOHAP-PROMO-CODE-2017] §2 PROMOTIONAL MATERIALS - INFORMATION TO BE MADE AVAILABLE:, PDF pp.4-5 (24.568) |
| H-06 | positive | 1 | weak | yes | [MOHAP-HEALTHAD-GUIDE] PDF pp.1-3 (14.294) |
| H-07 | positive | 1 | weak | yes | [UAE-AI-CHARTER-2024] PDF pp.1-3 (16.424) |
| H-08 | positive | 1 | weak | yes | [ITU-AIREADY-2] §19 What are the differences between the framework and the toolkit?, PDF pp.50-51 (14.55) |
| H-09 | positive | 1 | strong | yes | [UAE-PDPL-2021] Art. 4 Cases of Processing Personal Data without the Consent of its Owner (33.022) |
| HN-01 | negative | - | none | yes | [UAE-AI-STRATEGY-2031] Ecosystem For Ai, PDF pp.14-15 (6.31) |
| HN-02 | negative | - | none | yes | [ITU-AIREADY-2] §3 Structural Approach, PDF pp.24-25 (6.299) |
| HN-03 | negative | - | none | yes | [DHA-MEDAD-2022] §13 National Media Council (2019). Electronic Media System. Available on :, PDF pp.24-25 (6.946) |
| HN-04 | negative | - | none | yes | [DUBAI-AI-ETHICS-2022] §3.7.2 Guidelines, PDF p.20 (9.716) |
| HN-05 | negative | - | none | yes | [DUBAI-AI-ETHICS-2022] §3 From ISO/IEC 2382:2015, PDF p.7 (7.614) |
| HN-06 | negative | - | weak | yes | [DHA-AI-2021] §4 Policy Statement:, PDF pp.11-13 (10.184) |
| NEG-01 | negative | - | none | yes | [UAE-FL2-2019] PDF pp.15-16 (8.037) |
| NEG-02 | negative | - | none | yes | [TDRA-TAR-POLICY-V3] §12 Market Surveillance, PDF pp.8-9 (7.341) |
| NEG-03 | negative | - | none | yes | [DOH-AI-2018] About Department Of Health (Doh), PDF pp.3-5 (6.057) |
| GAP-01 | known_gap | - | weak | NO | [MOHAP-HEALTHAD-GUIDE] PDF pp.3-4 (21.316) |
| GAP-02 | known_gap | - | weak | NO | [UAE-FL2-2019] Art. 24, PDF p.24 (14.875) |
| GAP-03 | known_gap | - | weak | NO | [DHA-AI-2021] §5 References, PDF pp.16-17 (11.792) |
