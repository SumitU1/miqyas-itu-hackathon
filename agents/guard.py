"""Minimal safety guard for the Coach agent: a deterministic input check and output filter.

This is a fresh, small module written for this repo. It is NOT a copy of the Phase 1 miqyas-site
guard (whose output filter is still waiting for a human safety review). Keyword rules like these are
a floor, not a clinical safety system, and nobody qualified has reviewed them.
"""
from __future__ import annotations

import re

EMERGENCY = re.compile(
    r"chest pain|can'?t breathe|cannot breathe|short(ness)? of breath|kill myself|suicid|end my life|self[- ]harm"
    r"|unconscious|overdos|seizure|severe bleeding|slurred speech|speech slurred|weakness (on )?one side|face (is )?droop"
    r"|anaphyla",
    re.I,
)
EMERGENCY_REPLY = (
    "This sounds like it could be an emergency. Please call 999 (police and general emergency) or 998 (ambulance) "
    "now, or go to the nearest emergency department. I can't help with this in chat."
)

DOSE = re.compile(
    r"\b(take|taking|dose|dosage|increase|decrease|double|inject)\b[^.\n]{0,60}?\b\d+(\.\d+)?\s?(mg|mcg|µg|iu|ml|g|units?)\b"
    r"|\b\d+(\.\d+)?\s?(mg|mcg|µg|iu|ml|units?)\b[^.\n]{0,40}?\b(daily|twice|once|per day|a day|every)\b",
    re.I,
)
DIAGNOSIS = re.compile(
    r"\byou (have|had|are suffering from|suffer from|are diabetic|are anaemic|are anemic)\b(?! (a|an|the|some|any|no) (question|look|reference|visit|right|appointment))"
    r"|\b(you were|you are|you've been) diagnosed\b|\bthis (confirms|means you have)\b",
    re.I,
)
GUARANTEE = re.compile(r"\bguarantee[sd]?\b|\bcure[sd]?\b|\bno side effects\b", re.I)
# "cannot guarantee", "no supplement can guarantee", "not a cure", "nothing is guaranteed" deny a claim, they do not make one
NEGATED = re.compile(
    r"\b(?:cannot|can'?t|won'?t|will not|do(?:es)? not|don'?t|doesn'?t|never|not|no|nothing|nobody|no one)\b"
    r"(?:\W+\w+){0,4}?\W+(?:an?\s+)?(?:guarantee[sd]?|cure[sd]?)\b",
    re.I,
)

SAFE_REPLACEMENT = (
    "I can't give a diagnosis or a dose. I can explain what a result means in general terms and help you prepare "
    "questions for your clinician."
)


def input_guard(text: str) -> dict:
    if EMERGENCY.search(text or ""):
        return {"action": "emergency", "reply": EMERGENCY_REPLY}
    return {"action": "pass", "reply": None}


def output_guard(text: str) -> dict:
    if not isinstance(text, str):                       # a malformed model reply must not raise out of the guard
        text = "" if text is None else str(text)
    v, excerpts = [], {}
    for name, rx, hay in (("dose", DOSE, text), ("diagnosis", DIAGNOSIS, text), ("guarantee", GUARANTEE, NEGATED.sub(" ", text))):
        m = rx.search(hay)
        if m:
            v.append(name)
            excerpts[name] = hay[max(0, m.start() - 20):m.end() + 20].strip()    # what tripped it, for the reviewer
    if v:
        return {"ok": False, "violations": v, "text": SAFE_REPLACEMENT, "excerpts": excerpts}
    return {"ok": True, "violations": [], "text": text, "excerpts": {}}
