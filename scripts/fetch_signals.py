"""
Stage 1 — Harvest.

Pull real FDA drug-enforcement (recall) records from the openFDA API. No API key,
no npm, no paid data. Every record here is a real, publicly filed FDA enforcement
action — the same class of data Atlas Compliance's own product is built on.

Why recalls: a recall is the public, machine-readable tip of the FDA enforcement
iceberg. When a pharma firm files a Class I/II recall for a cGMP or sterility
failure, its quality/compliance team is — right then — living the exact problem
Atlas sells into. That is the buying trigger this engine detects.

Scope note (kept honest, surfaced on the site too): openFDA exposes recalls, not
Form 483s or Warning Letters. Those are in Atlas's fuller corpus but not in this
free feed. This engine detects one enforcement type well rather than pretending to
cover all three.
"""
import json
import os
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
ENDPOINT = "https://api.fda.gov/drug/enforcement.json"

# Pull the most recent enforcement actions. openFDA caps limit at 1000/request.
BATCH = 1000
TARGET = 1000  # one page of the freshest records is plenty of real signal


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "atlas-signal-engine/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    url = f"{ENDPOINT}?sort=report_date:desc&limit={BATCH}"
    print(f"GET {url}")
    payload = fetch(url)
    total_available = payload["meta"]["results"]["total"]
    results = payload["results"]
    print(f"openFDA reports {total_available:,} total drug-enforcement records.")
    print(f"Pulled the {len(results)} most recent by report_date.")

    # Keep only the fields we use, verbatim from FDA. No enrichment, no invention.
    keep = [
        "recall_number", "recalling_firm", "classification", "status",
        "report_date", "recall_initiation_date", "reason_for_recall",
        "product_description", "distribution_pattern", "voluntary_mandated",
        "state", "country", "city", "product_type", "event_id",
    ]
    cleaned = []
    for r in results:
        cleaned.append({k: r.get(k) for k in keep})

    os.makedirs(DATA, exist_ok=True)
    out = os.path.join(DATA, "raw_recalls.json")
    with open(out, "w") as f:
        json.dump({
            "source": ENDPOINT,
            "fetched_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
            "total_available": total_available,
            "records": cleaned,
        }, f, indent=2)
    print(f"Wrote {len(cleaned)} records -> {os.path.relpath(out)}")


if __name__ == "__main__":
    main()
