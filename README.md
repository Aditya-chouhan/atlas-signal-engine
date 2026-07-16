# Atlas Signal Engine

**A GTM signal engine built specifically for [Atlas Compliance](https://www.atlas-compliance.ai/).**

Atlas sells FDA compliance intelligence to pharma quality teams. The strongest
moment to reach one of those teams is the week it takes an FDA enforcement
action. This engine turns that logic into an outbound queue: it pulls **real**
FDA recall data, scores every firm for buying-trigger intensity, and drafts the
outreach — grounded only in what the FDA actually filed.

It mirrors Atlas's own product thesis. Enforcement data is the signal that powers
the product; here the same data powers the *go-to-market*.

**Live page:** `index.html` (static, self-contained, no build step).

---

## Pipeline

```
fetch_signals.py   → openFDA drug/enforcement API → data/raw_recalls.json   (1,000 most-recent real records)
score.py           → roll up to firm level, score 0–100 → data/scored_firms.json
generate_briefs.py → top-8 in-ICP firms → briefs + drafted outreach → data/briefs.json
build_site.py      → render everything → index.html
```

Run it end to end:

```bash
python3 scripts/fetch_signals.py
python3 scripts/score.py
python3 scripts/generate_briefs.py
python3 scripts/build_site.py
```

No API key. No paid data. No npm. Pure standard-library Python.

## Scoring (max 100, all disclosed)

| Input | Points | FDA field |
|---|---|---|
| Severity — worst classification (I / II / III) | 40 / 25 / 10 | `classification` |
| Recency — most recent event (<30 / <90 / <180d) | 25 / 18 / 10 | `report_date` |
| Systemic — distinct events (10+ / 4–9 / 2–3) | 20 / 14 / 8 | `event_id` |
| Quality-system reason flag (cGMP/sterility/impurity…) | +10 | `reason_for_recall` |
| Any event still Ongoing | +5 | `status` |

The score is a **buying-trigger score, not a quality verdict** — it measures how
acute and current a firm's compliance pain is (Atlas's best moment to help), not
whether the firm is "good" or "bad."

## Honesty guardrails

- Every firm, date, classification and reason is **real**, pulled verbatim from openFDA.
- **No fabricated contacts** — outreach targets a *role*, never an invented person/email.
- **No email is sent** — the drafts are composed examples written to a spec.
- **Scope stated plainly:** openFDA exposes recalls (one enforcement type). Form 483s
  and Warning Letters (Atlas's fuller corpus) are not in this free feed. This engine
  detects one signal well rather than pretending to cover all three.
- Some scored firms (Cipla, Zydus) are already Atlas customers — the engine flags
  accounts; a human dedupes against CRM.

## Data source

[openFDA drug/enforcement](https://open.fda.gov/apis/drug/enforcement/) — the public
FDA enforcement/recall API.

---

Built by Aditya Chouhan.
