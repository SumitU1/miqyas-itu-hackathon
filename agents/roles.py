"""Role definitions: mandate (which KB sources the role may query), what it may see, and what it must not do.

Scopes are source ids from sources/sources.json. They are disjoint for the three role agents, so each
sees a different slice of the law: that is the "different institutional mandates and information" the
brief asks for. The Adviser has no scope filter (whole KB). Four sources not yet downloaded are listed so
that they join the right scope automatically once the files exist in kb/raw/ and the KB is rebuilt.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Role:
    name: str
    title: str
    brief_role: str
    scope: tuple | None          # source ids; None = whole KB
    sees: str                    # description used in the prompt
    must_not: tuple = field(default_factory=tuple)


ROLES = {
    "coach": Role(
        "coach", "Miqyas Coach", "innovative AI solution",
        ("UAE-AI-CHARTER-2024", "UAE-AI-STRATEGY-2031", "DUBAI-AI-ETHICS-2022", "DHA-AI-2021", "DOH-AI-2018",
         "WHO-AI-HEALTH-2021"),
        "the member's synthetic record and the coach's own outputs",
        ("give a diagnosis or a dose", "move member data to anyone without a ruling and the member's consent"),
    ),
    "clinic": Role(
        "clinic", "Partner Clinic", "institutional participant (licensed facility)",
        ("DHA-HIS-2024", "DHA-TELEHEALTH-POL-2021", "DHA-TELEHEALTH-STD-V4", "DOH-HIE-2020", "DHA-MEDAD-2022",
         "MOHAP-HEALTHAD-GUIDE", "NMC-AD-GUIDE", "MOHAP-PROMO-CODE-2017", "UAE-FDL4-2016"),
        "only the records the member agreed to share with the clinic",
        ("read or ask for the rest of the member record",),
    ),
    "authority": Role(
        "authority", "Health-Data Authority", "regulator (MOHAP / DHA / DoH / UAE Data Office)",
        ("UAE-FL2-2019", "UAE-CR32-2020", "UAE-PDPL-2021", "MOHAP-MD51-2021", "DOH-ADHICS-V2", "TDRA-TAR-POLICY-V3",
         "TDRA-TAR-REG-V3", "TDRA-IOT-PROC-V1", "UAE-FDL38-2024", "UAE-FL15-2020"),
        "incident reports and data-flow descriptions, never clinical content",
        ("act without a documented trigger", "ask for clinical content"),
    ),
    "adviser": Role(
        "adviser", "Policy & Legal Adviser", "policy and legal adviser",
        None,
        "the questions and assessments sent to it, and the whole knowledge base",
        ("answer on weak or no evidence", "present a summary as the binding text", "give legal advice"),
    ),
}

AGENT_ROLES = ("coach", "clinic", "authority")
