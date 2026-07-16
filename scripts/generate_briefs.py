"""
Stage 3 — Brief + draft outreach.

For the top-scoring in-ICP firms, produce a Compliance Distress Brief: the real
enforcement facts, the buying-trigger diagnosis, the role to target, and a drafted
outreach email an Atlas SDR could send.

Hard honesty rules (same standard as the rest of the portfolio):
- Every fact in the email comes from the real openFDA record. Nothing invented.
- NO fabricated contact names or email addresses. We target a ROLE (the title the
  buyer holds), because inventing "Rajesh Kumar, VP Quality, rajesh@firm.com"
  would be fabrication. Role-targeting is what an SDR actually starts from.
- The email is a COMPOSED EXAMPLE written to a spec. It is not sent. No mail is
  transmitted anywhere by this script.
- The mapping from a firm's real recall reason to a specific Atlas module is the
  actual GTM insight being demonstrated — it is shown, not asserted.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

TOP_N = 8

# The person who owns this pain. Atlas's own JD names two: US Chief Quality
# Officers and Indian ops/compliance leaders. We target the title, never a
# fabricated individual.
ROLE_BY_SEGMENT = {
    "US pharma (CQO segment)": "Chief Quality Officer / VP of Quality",
    "India manufacturer (ops/compliance segment)":
        "Head of Quality Assurance / VP Regulatory Affairs",
}


def module_for_reason(terms, worst_class, n_events):
    """Map the real failure type to the Atlas capability that addresses it.

    Atlas's real modules (from atlas-compliance.ai): searchable 483/EIR/Warning
    Letter corpus, AI Copilot, supplier-risk monitoring, investigator/CFR trend
    analysis, peer benchmarking, Scout (SOP-vs-observation gap assessment).
    """
    t = set(terms)
    if {"nitroso", "nitrosamine", "impurit"} & t:
        return ("Peer benchmarking + CFR trend analysis",
                "See every other firm cited for the same nitrosamine/impurity "
                "class of observation, which investigators are driving it, and "
                "how they closed it out — before your next inspection.")
    if {"sterility", "sterile", "non-sterile", "contamination", "microbial",
        "endotoxin", "particulate"} & t:
        return ("Scout gap-assessment + investigator profiles",
                "Run your sterility/contamination SOPs against the real 483 "
                "observations in the same category, and pull the profile of the "
                "investigator most likely to cover your site.")
    if {"stability", "out of specification", "oos", "assay", "potency",
        "dissolution", "degradation"} & t:
        return ("483/EIR search + peer benchmarking",
                "Pull every 483 citing the same stability/OOS failure mode across "
                "peer manufacturers and see the corrective actions FDA accepted.")
    if worst_class == "Class I":
        return ("AI Copilot + Warning Letter corpus",
                "A Class I event draws follow-up scrutiny — see how peers who took "
                "Class I recalls fared at their next inspection, and what the "
                "recurring 483 themes were.")
    return ("Inspection intelligence search",
            "Benchmark this event against the full 483/EIR/Warning Letter corpus "
            "to see how comparable firms were cited and how they closed it.")


def clean(s):
    # openFDA text carries a few encoding artifacts (e.g. a mangled degree sign).
    # Fix only the known glyphs; never rewrite the substance of FDA's wording.
    return (s or "").replace("¿", "").replace("°", "deg ").strip()


def draft_email(firm):
    role = ROLE_BY_SEGMENT.get(firm["segment"], "Head of Quality")

    wc = firm["worst_classification"] or "recent"
    date = firm["most_recent_date"]
    reason = clean(firm["representative_reason"])
    # Trim the FDA reason to its first clause for the email hook (kept verbatim).
    hook = reason.split(". ")[0][:180]

    # Pick the Atlas module from THIS specific finding's own terms, so the email
    # hook and the pitched module are about the same event (not the firm's
    # aggregate history). Keeps the message coherent and honest.
    from score import QUALITY_SYSTEM_TERMS
    reason_terms = [t for t in QUALITY_SYSTEM_TERMS if t in reason.lower()]
    module, pitch = module_for_reason(
        reason_terms, firm["worst_classification"], firm["distinct_events"])

    if firm["distinct_events"] > 1:
        volume = (f"This isn't isolated — FDA records {firm['distinct_events']} "
                  f"distinct enforcement events for {firm['firm']} in the last "
                  f"~15 months.")
    else:
        volume = ""

    subject = f"{firm['firm']}: {wc} recall ({date}) — how peers closed the same finding"

    body = f"""Hi — sending this to whoever owns quality/compliance at {firm['firm']}.

I track FDA enforcement in real time. On {date}, {firm['firm']} filed a {wc} recall; the FDA reason on file reads: "{hook}". {volume}

The reason I'm reaching out: the teams that come out of an event like this cleanest are the ones who benchmark it fast — what the same observation looked like at peer manufacturers, which CFR sections and investigators keep recurring, and what corrective actions FDA actually accepted.

That's what Atlas does. {module}: {pitch}

We index 100,000+ inspection observations, 30,000+ Form 483s/EIRs and 11,800+ Warning Letters — searchable in seconds, at roughly a third of the cost of legacy tools. Cipla, Zydus, Torrent, Strides and Natco already run on it.

Worth a 20-minute look at your specific situation? I can pull the peer set for this exact finding before we even talk.

— [SDR name], Atlas Compliance
(This is a composed example for a portfolio demo. It has not been sent.)"""

    return {"target_role": role, "atlas_module": module, "subject": subject,
            "body": body}


def main():
    data = json.load(open(os.path.join(DATA, "scored_firms.json")))
    icp = [f for f in data["firms"] if f["in_icp"]][:TOP_N]

    briefs = []
    for f in icp:
        briefs.append({**f, "outreach": draft_email(f)})

    with open(os.path.join(DATA, "briefs.json"), "w") as fp:
        json.dump({"anchor_date": data["anchor_date"], "briefs": briefs}, fp, indent=2)

    print(f"Generated {len(briefs)} outreach briefs (top {TOP_N} in-ICP firms).\n")
    for b in briefs:
        print(f"[{b['score']}] {b['firm']}  ->  {b['outreach']['target_role']}")
        print(f"       module: {b['outreach']['atlas_module']}")
        print(f"       subject: {b['outreach']['subject']}\n")


if __name__ == "__main__":
    main()
