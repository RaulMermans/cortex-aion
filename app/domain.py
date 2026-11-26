"""Business interpretation of a bounded, already prepared Azure batch."""
from collections import Counter, defaultdict

FIELDS = ("unique_key", "agency", "complaint_type", "status", "closed_date", "quality_reason")
RULE = "CLOSED_WITHOUT_DATE"
MAX_ROWS = 10000

def investigate(silver, quarantine):
    """Return reviewable cases; do not infer causal explanations or citywide trends."""
    rows = silver + quarantine
    if not rows or len(rows) > MAX_ROWS:
        raise ValueError("Expected a nonempty bounded batch")
    for row in rows:
        if not all(field in row for field in FIELDS):
            raise ValueError("Unexpected source schema")
    keys = [str(r["unique_key"] or "").strip() for r in rows]
    if not all(keys) or len(set(keys)) != len(keys):
        raise ValueError("Batch has missing or repeated identifiers; review source selection")
    if any(r["quality_reason"] != "VALID" for r in silver) or any(
        not r["quality_reason"] or r["quality_reason"] == "VALID" for r in quarantine
    ):
        raise ValueError("Silver/quarantine routing is inconsistent")
    counts = Counter(r["agency"] or "Unknown" for r in rows)
    groups = defaultdict(list)
    for r in quarantine:
        if r["quality_reason"] == RULE:
            if str(r["status"] or "").strip().lower() != "closed" or str(r["closed_date"] or "").strip():
                raise ValueError("Closure exception does not match the recorded fields")
            groups[r["agency"] or "Unknown"].append(r)
    cases = []
    for agency, records in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        denominator = counts[agency]
        cases.append({
            "id": f"closure-{agency}",
            "agency": agency,
            "title": f"Closure records requiring review — {agency}",
            "affected": len(records),
            "agency_total": denominator,
            "exception_rate": round(100 * len(records) / denominator, 2),
            "categories": dict(Counter(r["complaint_type"] or "Unknown" for r in records)),
            "finding": "Requests marked Closed lack a recorded closing date.",
            "recommendation": "Review closure recording procedures; do not use these records to compute resolution-time KPIs.",
            "limitation": "The rule identifies a data inconsistency, not a confirmed operational failure. Root cause is unverified.",
            "evidence": [{k: r[k] for k in FIELDS} for r in records],
        })
    return {
        "batch_records": len(rows),
        "silver_records": len(silver),
        "quarantine_records": len(quarantine),
        "closure_exceptions": sum(len(r) for r in groups.values()),
        "other_exceptions": len(quarantine) - sum(len(r) for r in groups.values()),
        "cases": cases,
    }
