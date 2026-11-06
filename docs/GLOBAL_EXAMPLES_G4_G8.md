# Global (non-UAE) policy and standards examples for gaps G4 to G8

Prepared 2026-10-31 for the ITU AI for Good hackathon report (consumer health AI app + wearables).
Method: pages were retrieved with `mcp__parallel-search__web_fetch` / `web_search` (extract-based; it returns page excerpts, not a full browser render). "Confirmed by fetch" means the quoted text came back from a fetch of that exact URL. "Search excerpt only" means I saw it only in a search result. Public sources only, no private data. Quotes are 25 words or fewer, except the GDPR Art. 33 clause, which you asked for in exact wording (EU legislation, reuse permitted).

Summary of caveats up front:
- G4: the EU does have a coordination document for AI Act + MDR, but only for products with a medical purpose. I did not see GDPR addressed in it, and "no single rule owner for a non-device wellness coach" is our inference, not something the document says.
- G5: none of the three sources regulates claims generated at runtime by the AI itself. They regulate advertising and substantiation. The ASA text states the CAP Code covers ads, not the advertised product.
- G6: GDPR and the FTC rule both put a number in the instrument itself. I did NOT source a "delegates the period to regulations" example, so do not claim that contrast with a citation.
- G8: logging obligations exist (AI Act Arts. 12 and 19, ISO/IEC 42001 A.6.2.8). In what I could read, none defines a vocabulary for recording the legal basis or policy rule applied to each automated action. Paywalled full texts of ISO/IEC 23894 and the body of ISO/IEC 42001 were not read.

---

## G4. Overlapping AI-in-health regimes, no single rule owner

**Example name:** MDCG 2025-6 / AIB 2025-1, "Interplay between the Medical Devices Regulation (MDR) & In vitro Diagnostic Medical Devices Regulation (IVDR) and the Artificial Intelligence Act (AIA)"
| Field | Value |
|---|---|
| Issuer | Medical Device Coordination Group (MDCG) jointly with the Artificial Intelligence Board (AIB), European Commission DG SANTE |
| Date / version | June 2025 (published 19 June 2025), 27 pages, FAQ format |
| URL fetched | https://health.ec.europa.eu/system/files/2025-06/mdcg_2025-6_en.pdf |
| Landing page (search excerpt only) | https://health.ec.europa.eu/latest-updates/mdcg-2025-6-faq-interplay-between-medical-devices-regulation-vitro-diagnostic-medical-devices-2025-06-19_en |
| Quote (Introduction) | "a simultaneous and complementary application of the MDR/IVDR and the AIA for medical devices that contains one or more high-risk AI system." |
| Paraphrase | The EU's own guidance confirms that two regimes apply at once to AI medical devices: MDR/IVDR does not address AI-specific risks and the AI Act adds them, with a single conformity route through the MDR notified body and a single set of technical documentation (Art. 11(2) AIA). |
| Confidence | Confirmed by fetch |

Further points confirmed in the same fetch (usable as supporting facts):
- AI Act Art. 6(1) high-risk status for AI in medical devices depends on MDR/IVDR classification and notified-body involvement; the document says the AI Act "does not impact the risk classification" under MDR (paraphrased from Q on classification).
- Obligations for "Annex I high-risk AI systems" apply from 2 August 2027 (document's own date statement).
- The document says an MDAI that is not subject to third-party conformity assessment is not high-risk under Art. 6(1), "Nevertheless, other AIA obligations apply including but not limited to prohibited practices."

Limits for how we use it in the report:
- Scope is medical-purpose software only (MDR Art. 2(1) / IVDR Art. 2(2)). A direct-to-consumer coach that does not claim a medical purpose is outside the MDR and so outside this coordination mechanism. That is where the "no single owner" argument is strongest, but it is our inference.
- In the excerpts returned I did not see GDPR discussed. Do not cite this document for AI Act / MDR / GDPR three-way interplay. Not checked beyond excerpts.
- Alternative named in your brief, not fetched: WHO "Ethics and governance of artificial intelligence for health" (2021). Not checked (call budget).

---

## G5. Advertising and claims rules for AI-related and health claims

### G5-a (primary pick): FTC Operation AI Comply
| Field | Value |
|---|---|
| Name | "FTC Announces Crackdown on Deceptive AI Claims and Schemes" (Operation AI Comply) |
| Issuer | US Federal Trade Commission, press release |
| Date | 25 September 2024 |
| URL fetched | https://www.ftc.gov/news-events/news/press-releases/2024/09/ftc-announces-crackdown-deceptive-ai-claims-schemes |
| Quote (Chair Lina M. Khan) | "there is no AI exemption from the laws on the books." |
| Paraphrase | The FTC treats AI-based products as subject to existing deceptive and unfair practice law; the five announced cases involve AI-hype schemes, fake-review generation and an "AI Lawyer" claim, not health apps. |
| Confidence | Confirmed by fetch |

Caveat: the cases are not about health claims. Pair with G5-b for health substantiation.

### G5-b: FTC Health Products Compliance Guidance (health substantiation, includes an app example)
| Field | Value |
|---|---|
| Name | "Health Products Compliance Guidance" |
| Issuer | US FTC, Bureau of Consumer Protection staff guidance |
| Date | December 2022 (press release dated 2022-12-20; PDF metadata 2022-12-13) |
| URLs | https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance ; PDF https://www.ftc.gov/system/files/ftc_gov/pdf/Health-Products-Compliance-Guidance.pdf |
| Quote | "The FTC's substantiation standard is a rigorous one, particularly when claims relate to health." |
| Paraphrase | Health claims need competent and reliable scientific evidence, generally human clinical testing for health benefit claims; Example 14 is a smartphone app marketed for acne whose "entertainment only" disclaimer cannot contradict the express claim. |
| Confidence | Search excerpt only (not separately fetched) |

### G5-c: UK CAP/ASA, AI products in ads
| Field | Value |
|---|---|
| Name | "Regulating the Illusion of Intelligence in Ads" (CAP News) |
| Issuer | UK Committee of Advertising Practice / Advertising Standards Authority |
| Date | 27 August 2026 |
| URL fetched | https://www.asa.org.uk/news/regulating-the-illusion-of-intelligence-in-ads.html |
| Quote | "Unless you can provide evidence of the product's health hacks, keep your AI from playing doctor." |
| Second quote | "Unless and until there is AI-specific legislation" (the article then applies the existing CAP Code) |
| Paraphrase | The UK ad regulator applies existing substantiation and responsibility rules to ads for AI health and wellness assistants and says it cannot comment on the AI product's own behaviour, only on how it is presented in ads. |
| Confidence | Confirmed by fetch |

Supporting UK rules (search excerpt only): CAP Code rule 12.1 requires objective health claims to be backed by evidence, "if relevant consisting of trials conducted on people" (https://www.asa.org.uk/resource/health-beauty-and-slimming-claims-substantiation.html, guidance dated 2010 on the page, PDF metadata 2017).

Gap statement supported by these sources: advertising law reaches what the company says about the AI. None of the three addresses the personalised claim the AI generates inside the app at runtime. I did not find a regulator document on that point; say "not found in sources checked", not "does not exist".

---

## G6. Breach-notification timing

### G6-a: GDPR Article 33(1)
| Field | Value |
|---|---|
| Name | Regulation (EU) 2016/679 (GDPR), Art. 33 "Notification of a personal data breach to the supervisory authority" |
| Issuer | European Parliament and Council |
| Date | 27 April 2016 (EUR-Lex record date) |
| URL fetched | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679 |
| Exact wording (Art. 33(1)) | "In the case of a personal data breach, the controller shall without undue delay and, where feasible, not later than 72 hours after having become aware of it, notify the personal data breach to the supervisory authority competent in accordance with Article 55, unless the personal data breach is unlikely to result in a risk to the rights and freedoms of natural persons." |
| Second subparagraph | "Where the notification to the supervisory authority is not made within 72 hours, it shall be accompanied by reasons for the delay." |
| Art. 33(2) | "The processor shall notify the controller without undue delay after becoming aware of a personal data breach." |
| Paraphrase | The number of hours is written into the statute itself, with a "where feasible" qualifier and a duty to explain delay. |
| Confidence | Confirmed by fetch |

### G6-b: US FTC Health Breach Notification Rule, 16 CFR 318.4
| Field | Value |
|---|---|
| Name | 16 CFR 318.4 "Timeliness of notification" |
| Issuer | US FTC, eCFR |
| Date / version | eCFR page metadata 2024-07-29 (current version as returned) |
| URL fetched | https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-318/section-318.4 |
| Quote 318.4(a) | "shall be sent without unreasonable delay and in no case later than 60 calendar days after the discovery of a breach of security." |
| Quote 318.4(b) | "shall be provided contemporaneously with the notice required by paragraph (a)" (this is the FTC notice for breaches involving 500 or more individuals) |
| Paraphrase | The 60 calendar day outer limit applies to notices to individuals, media and third-party-service-provider notices (via 318.3(a)(1), (a)(3), (b)); FTC notice for 500+ individuals is due at the same time; breaches of fewer than 500 individuals may be logged and sent to the FTC annually within 60 days after the end of the calendar year. |
| Confidence | Confirmed by fetch. The "500 or more individuals" threshold for FTC notice is in 318.4(b) text; the separate media-notice population threshold sits in 318.3, which I did not fetch. |

### Contrast requested (statute fixes the number vs delegates to regulation)
Not sourced. Both examples above state a period in the instrument itself (GDPR in the statute; the FTC number is in a regulation made under statute). I did not locate or fetch a law that delegates the period to later regulations. If the report needs that contrast, it needs a separate source; do not assert it without one.

---

## G8. Is there a standard vocabulary for recording the legal basis or policy rule applied to an automated AI action in an audit log?

What I checked and what each page confirms about logging. "Legal basis / rule vocabulary" below means a defined set of fields or terms for recording which legal basis or policy rule justified a specific automated action.

### G8-a: EU AI Act, Articles 12 and 19
| Field | Value |
|---|---|
| Name | Regulation (EU) 2024/1689 (AI Act), Art. 12 "Record-keeping" and Art. 19 "Automatically generated logs" |
| Issuer | European Parliament and Council |
| Date | 13 June 2024; OJ L, 2024/1689, 12.7.2024 |
| URL fetched | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689 |
| Quote Art. 12(1) | "High-risk AI systems shall technically allow for the automatic recording of events (logs) over the lifetime of the system." |
| Quote Art. 12(2) lead-in | "logging capabilities shall enable the recording of events relevant for:" (the list (a) to (c) was cut off in the fetched excerpt; I did not read it) |
| Quote Art. 19(1) | "of at least six months, unless provided otherwise in the applicable Union or national law" (retention; text continues "in particular in Union law on the protection of personal data") |
| Paraphrase | Mandatory event logging and minimum six-month retention for high-risk systems, with traceability as the stated purpose; the excerpts I read do not prescribe recording the legal basis or rule behind each action. |
| Confidence | Confirmed by fetch for Art. 12(1), 12(2) lead-in, 19(1). Art. 12(2)(a) to (c) not seen. |

Also confirmed in the MDCG 2025-6 fetch: it paraphrases Art. 12 as requiring logs "of system performance and behaviour throughout their lifecycle" to support monitoring and post-market monitoring (document's own wording, not the Act's). Scope reminder: Art. 12 applies to high-risk AI systems only; a wellness coach outside the high-risk categories is not bound by it.

### G8-b: ISO/IEC 42001:2023 (AI management systems)
| Field | Value |
|---|---|
| Name | ISO/IEC 42001:2023 Information technology, Artificial intelligence, Management system |
| Issuer | ISO/IEC JTC 1/SC 42 |
| Date | Edition 1, published 2023-12 (2023-12-18 on life-cycle table) |
| URL fetched | https://www.iso.org/standard/81230.html |
| What the public page says | Lists "Traceability, transparency and reliability" among benefits and describes a management-system standard using Plan-Do-Check-Act. The page does not mention logs, records or audit trails. |
| Quote (public page) | "Traceability , transparency and reliability" (benefits list) |
| Confidence | Confirmed by fetch that the public ISO page itself says nothing about logging. |

Annex A control A.6.2.8 "AI system recording of event logs" (control text not on the ISO public page). Seen in search results only, as reproductions on third-party sites, not ISO's own page:
- Third-party PDF copy of the standard text: http://www.wd-cert.com/upload/files/2025/8/729a0b031a2c59e1.pdf (provenance and licence unclear, treat with caution).
- Third-party control library: https://controlstack.au/controls/iso42001-annex-a-6-2-8-ai-system-recording-of-event-logs
- Quote as shown in both: "record keeping of event logs should be enabled, but at the minimum when the AI system is in use."
- The guidance text shown in the PDF copy (B.6.2.8) lists examples such as traceability of functionality and "which events should be monitored and how event logs are prioritized and reviewed". It leaves fields open. One other site (learn.daydream.ai) shows a different "verbatim" sentence for the control ("The organization shall implement event logging for AI systems"); it conflicts with the two above, so I discarded it.
- Confidence: Search excerpt only, third-party reproduction. To cite the control in the report, buy or access the standard via ISO OBP, or cite as "per the text of Annex A as reproduced by third parties".

### G8-c: ISO/IEC 23894:2023 (AI risk management guidance)
| Field | Value |
|---|---|
| Issuer / date | ISO/IEC JTC 1/SC 42, Edition 1, 2023-02 (published 2023-02-06) |
| URL fetched | https://www.iso.org/standard/77304.html |
| Quote (abstract) | "can manage risk specifically related to AI." |
| What the public page says | Abstract and catalogue data only. No mention of logging, records or audit trail. |
| Confidence | Confirmed by fetch (public page only; full text paywalled and not read). |

### G8-d: NIST AI RMF 1.0, GOVERN function
| Field | Value |
|---|---|
| Name | Artificial Intelligence Risk Management Framework (AI RMF 1.0), NIST AI 100-1 |
| Issuer | US National Institute of Standards and Technology |
| Date | January 2023 |
| URLs fetched | https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf ; https://airc.nist.gov/airmf-resources/airmf/5-sec-core/ |
| Quote (GOVERN 1.1) | "Legal and regulatory requirements involving AI are understood, managed, and documented." |
| Second quote (GOVERN intro) | "Documentation can enhance transparency, improve human review processes, and bolster accountability in AI system teams." |
| What the GOVERN table says | I read the full list of GOVERN subcategories (1.1 to 1.7, 2.1 to 2.3, 3.1 to 3.2, 4.1 to 4.3, 5.1 to 5.2, 6.1 to 6.2). None mentions event logs, audit logs or per-action records. Legal compliance appears only at organisation level (1.1). Incident tracking is in MANAGE 4.3, not GOVERN. |
| Confidence | Confirmed by fetch for the airc.nist.gov core table; the PDF returned partial excerpts only. |

### G8 conclusion supportable from what I checked
- What exists: mandatory event logging for high-risk systems with minimum retention (AI Act Arts. 12, 19); an event-log control in ISO/IEC 42001 (A.6.2.8, text only verified through third-party reproductions); organisation-level documentation of legal requirements (NIST GOVERN 1.1).
- What I did not find in the sources read: a defined vocabulary or schema for recording, per automated action, which legal basis or policy rule was applied. Safe wording for the report: "In the public pages and texts we reviewed (AI Act Arts. 12 and 19, the public ISO/IEC 42001 and 23894 pages, ISO/IEC 42001 A.6.2.8 as reproduced by third parties, NIST AI RMF GOVERN), we found logging requirements but no vocabulary for recording the legal basis or rule applied to an individual automated action." Add: "The paid full texts of ISO/IEC 23894 and the ISO/IEC 42001 body, and AI Act Art. 12(2)(a) to (c), were not read."
- Not checked at all: GDPR Art. 30 / Art. 5(2) accountability records, ISO/IEC 27001 / 27701 logging controls, ISO/IEC 42005, any CEN-CENELEC JTC 21 harmonised standard drafts for AI Act Art. 12. These are the likeliest places a counter-example would live.

---

## US state example: Washington My Health My Data Act (RCW chapter 19.373)

| Field | Value |
|---|---|
| Name | Washington My Health My Data Act, chapter 19.373 RCW (Laws of 2023, ch. 191, ESHB 1155) |
| Issuer | Washington State Legislature |
| Statute index URL fetched | https://app.leg.wa.gov/RCW/default.aspx?cite=19.373 |
| Definitions URL fetched | https://app.leg.wa.gov/RCW/default.aspx?cite=19.373.010 |
| Session law URL fetched | https://lawfilesext.leg.wa.gov/biennium/2023-24/Pdf/Bills/Session%20Laws/House/1155-S.SL.pdf |
| Dates | Approved by Governor 27 April 2023. Session-law header: "EFFECTIVE DATE: July 23, 2023". Operative duties for regulated entities start 31 March 2024 (e.g. RCW 19.373.020, 19.373.070 "beginning March 31, 2024"); small businesses must comply from 30 June 2024. |
| Definition (RCW 19.373.010(8)(a)) | "Consumer health data" means personal information "linked or reasonably linkable to a consumer and that identifies the consumer's past, present, or future physical or mental health status." |
| Inference clause (010(8)(b)(xiii)) | covers data "derived or extrapolated from nonhealth information (such as proxy, derivative, inferred, or emergent data by any means, including algorithms or machine learning)." |
| Paraphrase | The statute covers health data held by apps and websites that HIPAA does not reach, and expressly includes health information inferred by algorithms or machine learning from non-health data. |
| Purpose statement (RCW 19.373.005(2), paraphrase) | The legislature notes HIPAA covers only specific health care entities, and that data collected by noncovered entities such as certain apps and websites lacks the same protection. |
| Confidence | Confirmed by fetch (definition, dates, purpose). Which date to call "took effect": the law took effect 23 July 2023 per the session-law header; its compliance start dates are 31 March 2024 and 30 June 2024. State both to avoid error. |

---

## Tool-call note
About 14 search/fetch calls used. Not checked: WHO 2021 guidance; a statute that delegates the breach period to regulations; GDPR Art. 30; harmonised standards for AI Act Art. 12.
