"""Rule-based medication review flags.

Flags are raised only from (a) the patient's own recorded data and (b) the
small curated reference table below. MyKshema does not invent interaction
information, and never prescribes, stops or changes medicines. Every flag
requires review by a qualified clinician.
"""
from __future__ import annotations

from .. import models as m

REFERENCE_NOTE = (
    "MyKshema demo reference table: a small curated subset of widely documented interactions (as described in "
    "standard references such as national formularies and product labelling). It is NOT a complete clinical "
    "drug-interaction database. Verify in an authoritative source before acting."
)

# (match_a, match_b, severity, summary). A match is a generic name or a drug class (lower-case).
INTERACTIONS: list[tuple[str, str, str, str]] = [
    ("nsaid", "angiotensin receptor blocker", "moderate",
     "NSAIDs can reduce the blood-pressure-lowering effect of ARBs and, especially with reduced kidney function, "
     "increase the risk of kidney injury and high potassium."),
    ("nsaid", "ace inhibitor", "moderate",
     "NSAIDs can reduce the blood-pressure-lowering effect of ACE inhibitors and increase the risk of kidney injury."),
    ("warfarin", "nsaid", "high", "Combining warfarin with NSAIDs increases bleeding risk."),
    ("warfarin", "aspirin", "high", "Combining warfarin with aspirin increases bleeding risk."),
    ("clopidogrel", "omeprazole", "moderate", "Omeprazole can reduce the antiplatelet effect of clopidogrel."),
    ("clopidogrel", "esomeprazole", "moderate", "Esomeprazole can reduce the antiplatelet effect of clopidogrel."),
    ("simvastatin", "clarithromycin", "high", "Clarithromycin raises simvastatin levels, increasing myopathy risk."),
    ("sildenafil", "nitrate", "high", "Sildenafil with nitrates can cause severe low blood pressure."),
    ("ace inhibitor", "spironolactone", "moderate", "ACE inhibitors with spironolactone can raise potassium levels."),
    ("angiotensin receptor blocker", "spironolactone", "moderate",
     "ARBs with spironolactone can raise potassium levels."),
]

# Classes where two concurrent agents usually indicate possible duplicate therapy.
DUPLICATE_CLASSES = {
    "statin", "angiotensin receptor blocker", "ace inhibitor", "sulfonylurea", "biguanide", "nsaid",
    "proton pump inhibitor", "beta blocker", "dpp-4 inhibitor", "sglt2 inhibitor",
}

CURRENT = {"active", "patient_reported", "proposed"}


def _keys(med: m.Medication) -> set[str]:
    keys = set()
    for v in (med.generic_name, med.drug_class, med.name):
        if v:
            keys.add(v.lower().strip())
    if med.name:
        keys.add(med.name.lower().split()[0])
    return keys


def review(meds: list[m.Medication], allergies: list[m.Allergy]) -> list[dict]:
    flags: list[dict] = []
    current = [x for x in meds if x.status in CURRENT]

    def flag(ftype: str, severity: str, title: str, detail: str, involved: list[m.Medication], evidence: str) -> None:
        flags.append({
            "id": f"flag_{len(flags) + 1}", "type": ftype, "severity": severity, "title": title, "detail": detail,
            "medication_ids": [x.id for x in involved], "medication_names": [x.name for x in involved],
            "evidence": evidence, "requires_clinician_review": True,
        })

    # 1. duplicates: same generic, or same class within duplicate-prone classes
    seen_pairs: set[frozenset] = set()
    for i, a in enumerate(current):
        for b in current[i + 1:]:
            pair = frozenset((a.id, b.id))
            ga, gb = (a.generic_name or "").lower(), (b.generic_name or "").lower()
            ca, cb = (a.drug_class or "").lower(), (b.drug_class or "").lower()
            if ga and ga == gb:
                seen_pairs.add(pair)
                flag("duplicate", "moderate", f"Possible duplicate: {a.name} and {b.name}",
                     f"Both records are the same medicine ({ga}). Check whether one entry is outdated.", [a, b],
                     "Patient medication list")
            elif ca and ca == cb and ca in DUPLICATE_CLASSES:
                seen_pairs.add(pair)
                who = {x.prescribed_by or "patient-reported" for x in (a, b)}
                flag("duplicate_class", "moderate", f"Possible duplicate therapy: two {ca}s",
                     f"{a.name} and {b.name} are both recorded as current {ca} therapy "
                     f"(from: {', '.join(sorted(who))}). Confirm whether one was meant to replace the other.",
                     [a, b], "Patient medication list; drug class as recorded")

    # 2. interactions from curated table
    for i, a in enumerate(current):
        for b in current[i + 1:]:
            ka, kb = _keys(a), _keys(b)
            for x, y, sev, summary in INTERACTIONS:
                if (x in ka and y in kb) or (x in kb and y in ka):
                    flag("interaction", sev, f"Known interaction to review: {a.name} + {b.name}", summary, [a, b],
                         REFERENCE_NOTE)
                    break

    # 3. documented allergy conflicts (exact class / substance match only)
    for alg in allergies:
        akeys = {k for k in ((alg.drug_class or "").lower(), alg.substance.lower().split(" ")[0]) if k}
        for med in meds:
            mkeys = _keys(med)
            if akeys & mkeys or any(k in alg.substance.lower() for k in mkeys if len(k) > 4):
                is_current = med.status in CURRENT
                flag("allergy_conflict", "high" if is_current else "info",
                     f"{'Allergy conflict' if is_current else 'Historical allergy match'}: {med.name}",
                     f"Documented allergy to {alg.substance} (reaction: {alg.reaction or 'not documented'}). "
                     + ("This medicine is recorded as current." if is_current else
                        f"This medicine is recorded as {med.status} - likely the cause of the recorded reaction; "
                        "kept for history."),
                     [med], "Patient allergy record")

    # 4. missing / inconsistent details
    for med in current:
        missing = [label for label, v in (("dosage", med.dosage), ("frequency", med.frequency)) if not v]
        if missing:
            flag("missing_details", "low", f"Missing {' and '.join(missing)}: {med.name}",
                 f"The record for {med.name} has no {' or '.join(missing)}. Ask the patient or check the source.",
                 [med], "Patient medication list")
        if med.status == "patient_reported" and not med.verified:
            flag("unverified", "info", f"Patient-reported, not clinician-verified: {med.name}",
                 med.notes or "Self-reported medicine; confirm details.", [med], "Patient report")
    order = {"high": 0, "moderate": 1, "low": 2, "info": 3}
    flags.sort(key=lambda f: order.get(f["severity"], 9))
    for n, f in enumerate(flags, start=1):
        f["id"] = f"flag_{n}"
    return flags
