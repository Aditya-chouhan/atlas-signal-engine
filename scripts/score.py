"""
Stage 2 — Score.

Roll raw recall records up to the FIRM (account) level and score each firm for
Atlas-fit: how strong a buying trigger is this firm's current enforcement
situation for a compliance-intelligence platform?

Design choices, all disclosed and defensible:

1. Aggregate by firm, count DISTINCT enforcement events (event_id), not raw
   recall_numbers. One recall event routinely spans dozens of NDCs/lots; counting
   recall_numbers would punish a firm for SKU breadth, not for having more
   problems. Distinct events is the honest measure of "how many separate times
   did FDA act against this firm in the window."

2. The score is a buying-trigger score, not a quality verdict on the firm. A high
   score means "acute, current, inspection-grade compliance pain" — the moment
   Atlas's product is most valuable — NOT "this is a bad company."

Weights (max 100), each mapped to a real openFDA field:

   Severity (worst classification)      Class I 40 / Class II 25 / Class III 10
   Recency (most recent event)          <30d 25 / <90d 18 / <180d 10 / else 3
   Systemic (distinct events)           1: 0 / 2-3: 8 / 4-9: 14 / 10+: 20
   Quality-system reason flag           +10 if any cGMP/sterility/impurity/etc.
   Ongoing status                       +5 if any event still Ongoing

The quality-system flag is what separates a manufacturer's cGMP failure (Atlas's
core ICP — a quality-system problem their platform maps to Form 483 patterns)
from a distributor's labeling/logistics recall (weaker fit). It is applied by
matching the FDA's own reason_for_recall text, shown per firm so it is auditable.
"""
import json
import os
import re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

# "Today" is pinned to the freshest report_date in the dataset so recency scoring
# is reproducible regardless of when the script is re-run against a saved pull.
# (openFDA data lags real time; anchoring to the data's own max date is honest.)
QUALITY_SYSTEM_TERMS = [
    "cgmp", "current good manufacturing", "sterility", "sterile", "non-sterile",
    "contamination", "microbial", "nitroso", "nitrosamine", "impurit",
    "stability", "out of specification", "oos", "cross-contamination",
    "particulate", "endotoxin", "data integrity", "assay", "degradation",
    "dissolution", "potency", "superpotent", "subpotent", "fails",
]

SEVERITY_PTS = {"Class I": 40, "Class II": 25, "Class III": 10}
CLASS_RANK = {"Class I": 1, "Class II": 2, "Class III": 3}

INDIA = "India"


def parse_date(s):
    try:
        return datetime.strptime(s, "%Y%m%d")
    except (ValueError, TypeError):
        return None


def recency_pts(days):
    if days is None:
        return 3
    if days <= 30:
        return 25
    if days <= 90:
        return 18
    if days <= 180:
        return 10
    return 3


def systemic_pts(n_events):
    if n_events >= 10:
        return 20
    if n_events >= 4:
        return 14
    if n_events >= 2:
        return 8
    return 0


def worst_class(classes):
    ranked = [c for c in classes if c in CLASS_RANK]
    if not ranked:
        return None
    return min(ranked, key=lambda c: CLASS_RANK[c])


def main():
    raw = json.load(open(os.path.join(DATA, "raw_recalls.json")))
    records = raw["records"]

    # Data-anchored "today": the newest report_date present.
    all_dates = [parse_date(r["report_date"]) for r in records]
    today = max(d for d in all_dates if d)

    firms = {}
    for r in records:
        name = (r.get("recalling_firm") or "Unknown").strip()
        f = firms.setdefault(name, {
            "firm": name, "events": set(), "recall_numbers": set(), "lines": 0,
            "classes": [], "statuses": set(), "reasons": [],
            "dates": [], "country": r.get("country"), "state": r.get("state"),
            "city": r.get("city"), "products": [],
        })
        f["lines"] += 1
        if r.get("event_id"):
            f["events"].add(r["event_id"])
        if r.get("recall_number"):
            f["recall_numbers"].add(r["recall_number"])
        f["classes"].append(r.get("classification"))
        f["statuses"].add(r.get("status"))
        if r.get("reason_for_recall"):
            f["reasons"].append(r["reason_for_recall"])
        d = parse_date(r.get("report_date"))
        if d:
            f["dates"].append(d)
        if r.get("product_description"):
            f["products"].append(r["product_description"])

    scored = []
    for name, f in firms.items():
        n_events = len(f["events"]) or 1
        wc = worst_class(f["classes"])
        most_recent = max(f["dates"]) if f["dates"] else None
        days_since = (today - most_recent).days if most_recent else None

        reason_blob = " ".join(f["reasons"]).lower()
        matched_terms = sorted({t for t in QUALITY_SYSTEM_TERMS if t in reason_blob})
        quality_flag = bool(matched_terms)
        ongoing = "Ongoing" in f["statuses"]

        sev = SEVERITY_PTS.get(wc, 0)
        rec = recency_pts(days_since)
        sysm = systemic_pts(n_events)
        qual = 10 if quality_flag else 0
        ong = 5 if ongoing else 0
        score = sev + rec + sysm + qual + ong

        # Atlas ICP segment tag (their two named segments)
        country = (f["country"] or "").strip()
        if country == "United States":
            segment = "US pharma (CQO segment)"
        elif country == INDIA:
            segment = "India manufacturer (ops/compliance segment)"
        else:
            segment = f"Other ({country or 'unknown'})"
        in_icp = country in ("United States", INDIA)

        # A representative real reason (longest = usually most specific)
        rep_reason = max(f["reasons"], key=len) if f["reasons"] else ""

        scored.append({
            "firm": name,
            "score": score,
            "components": {"severity": sev, "recency": rec, "systemic": sysm,
                           "quality_system": qual, "ongoing": ong},
            "worst_classification": wc,
            "distinct_events": n_events,
            # Count the raw enforcement lines rolled up for this firm, NOT
            # len(recall_numbers): openFDA leaves `recall_number` blank on some
            # filings, and a firm whose only line has a blank recall_number was
            # previously reported as total_recall_lines: 0 despite having a real
            # enforcement event (caught by gtm-data-quality-monitor, which flagged
            # ALEMBIC PHARMACEUTICALS, INC. as distinct_events=1 / lines=0).
            # Scoring is unaffected — `systemic` has always used distinct events.
            "total_recall_lines": f["lines"],
            "distinct_recall_numbers": len(f["recall_numbers"]),
            "most_recent_date": most_recent.strftime("%Y-%m-%d") if most_recent else None,
            "days_since_recent": days_since,
            "any_ongoing": ongoing,
            "quality_system_flag": quality_flag,
            "quality_terms_matched": matched_terms,
            "segment": segment,
            "in_icp": in_icp,
            "country": country,
            "state": f.get("state"),
            "city": f.get("city"),
            "representative_reason": rep_reason,
            "example_product": (f["products"][0] if f["products"] else "")[:160],
        })

    scored.sort(key=lambda x: (-x["score"], -x["distinct_events"]))

    out = {
        "anchor_date": today.strftime("%Y-%m-%d"),
        "firms_scored": len(scored),
        "weights_doc": "See score.py header — max 100.",
        "firms": scored,
    }
    with open(os.path.join(DATA, "scored_firms.json"), "w") as fp:
        json.dump(out, fp, indent=2)

    print(f"Anchor date (data max): {today:%Y-%m-%d}")
    print(f"Scored {len(scored)} distinct firms.")
    print("\nTop 12 by Atlas-fit score:")
    print(f"{'score':>5}  {'evt':>3}  {'class':<9} {'seg':<38} firm")
    for s in scored[:12]:
        seg = s["segment"][:36]
        print(f"{s['score']:>5}  {s['distinct_events']:>3}  "
              f"{(s['worst_classification'] or '-'):<9} {seg:<38} {s['firm'][:40]}")


if __name__ == "__main__":
    main()
