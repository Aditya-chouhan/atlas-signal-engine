"""
Stage 4 — Render the static site (index.html). Self-contained, no external
assets, no build step. Reads the real pipeline outputs and renders them.
"""
import json
import os
import html

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
ROOT = os.path.join(HERE, "..")


def esc(s):
    s = str(s if s is not None else "")
    # Same source-glyph cleanup used in the email step (mangled degree sign etc.)
    s = s.replace("¿", "").replace("�", "")
    return html.escape(s)


def load():
    raw = json.load(open(os.path.join(DATA, "raw_recalls.json")))
    scored = json.load(open(os.path.join(DATA, "scored_firms.json")))
    briefs = json.load(open(os.path.join(DATA, "briefs.json")))
    return raw, scored, briefs


def score_bar(components):
    labels = {"severity": "Severity", "recency": "Recency",
              "systemic": "Systemic", "quality_system": "Quality-system",
              "ongoing": "Ongoing"}
    parts = []
    for k, v in components.items():
        if v:
            parts.append(f'<span class="chip">{labels[k]} +{v}</span>')
    return "".join(parts)


def leaderboard_rows(firms):
    rows = []
    for i, f in enumerate(firms[:25], 1):
        icp = "in-icp" if f["in_icp"] else "out-icp"
        qual = "yes" if f["quality_system_flag"] else "—"
        rows.append(f"""
        <tr class="{icp}">
          <td class="rank">{i}</td>
          <td class="score"><b>{f['score']}</b></td>
          <td class="firm">{esc(f['firm'])}</td>
          <td>{esc(f['worst_classification'] or '—')}</td>
          <td class="num">{f['distinct_events']}</td>
          <td>{esc(f['most_recent_date'] or '—')}</td>
          <td class="qs">{qual}</td>
          <td class="seg">{esc(f['segment'])}</td>
        </tr>""")
    return "".join(rows)


def brief_cards(briefs):
    cards = []
    for b in briefs:
        o = b["outreach"]
        terms = ", ".join(b["quality_terms_matched"][:6]) or "—"
        body = esc(o["body"]).replace("\n", "<br>")
        cards.append(f"""
        <div class="brief">
          <div class="brief-head">
            <div>
              <div class="brief-firm">{esc(b['firm'])}</div>
              <div class="brief-sub">{esc(b['segment'])} · {esc(b['city'] or '')} {esc(b['state'] or '')} {esc(b['country'])}</div>
            </div>
            <div class="brief-score">{b['score']}<span>/100</span></div>
          </div>
          <div class="brief-grid">
            <div><span class="k">Worst classification</span>{esc(b['worst_classification'])}</div>
            <div><span class="k">Distinct FDA events (15mo)</span>{b['distinct_events']}</div>
            <div><span class="k">Most recent</span>{esc(b['most_recent_date'])} ({b['days_since_recent']}d before anchor)</div>
            <div><span class="k">Status</span>{'Ongoing' if b['any_ongoing'] else 'Closed'}</div>
          </div>
          <div class="score-chips">{score_bar(b['components'])}</div>
          <div class="reason"><span class="k">FDA reason on file (verbatim)</span>{esc(b['representative_reason'][:320])}{'…' if len(b['representative_reason'])>320 else ''}</div>
          <div class="qterms"><span class="k">Quality-system terms matched</span>{esc(terms)}</div>
          <div class="target"><span class="k">Target role</span>{esc(o['target_role'])} &nbsp;·&nbsp; <span class="k">Atlas module</span>{esc(o['atlas_module'])}</div>
          <details class="email">
            <summary>Drafted outreach email (composed to spec — not sent)</summary>
            <div class="email-subj"><b>Subject:</b> {esc(o['subject'])}</div>
            <div class="email-body">{body}</div>
          </details>
        </div>""")
    return "".join(cards)


def main():
    raw, scored, briefs = load()
    firms = scored["firms"]
    n_icp = sum(1 for f in firms if f["in_icp"])
    n_classI = sum(1 for f in firms if f["worst_classification"] == "Class I")
    india = sum(1 for f in firms if f["country"] == "India")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Atlas Signal Engine — FDA enforcement as a buying trigger</title>
<style>
  :root {{
    --ink:#0d1b2a; --muted:#5a6b7b; --line:#e3e8ee; --bg:#f6f8fb;
    --card:#fff; --accent:#1b4965; --hot:#c1121f; --ok:#2a9d8f; --chip:#eef3f8;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); background:var(--bg); }}
  .wrap {{ max-width:1040px; margin:0 auto; padding:0 20px; }}
  header {{ background:linear-gradient(160deg,#0d1b2a,#1b4965); color:#fff; padding:56px 0 44px; }}
  header .tag {{ display:inline-block; font-size:12px; letter-spacing:.14em; text-transform:uppercase;
                opacity:.8; border:1px solid rgba(255,255,255,.3); padding:4px 10px; border-radius:20px; }}
  header h1 {{ font-size:34px; line-height:1.2; margin:16px 0 10px; }}
  header p {{ font-size:18px; opacity:.92; max-width:720px; margin:0; }}
  .stats {{ display:flex; flex-wrap:wrap; gap:14px; margin-top:26px; }}
  .stat {{ background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.15); border-radius:10px;
           padding:12px 16px; }}
  .stat b {{ display:block; font-size:24px; }}
  .stat span {{ font-size:12.5px; opacity:.85; }}
  section {{ padding:38px 0; }}
  h2 {{ font-size:22px; margin:0 0 6px; }}
  h2 + .lede {{ color:var(--muted); margin:0 0 22px; max-width:760px; }}
  .thesis {{ background:var(--card); border:1px solid var(--line); border-left:4px solid var(--accent);
             border-radius:10px; padding:20px 22px; }}
  .thesis p {{ margin:0 0 10px; }}
  .thesis p:last-child {{ margin:0; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line);
           border-radius:10px; overflow:hidden; font-size:14px; }}
  th,td {{ text-align:left; padding:9px 11px; border-bottom:1px solid var(--line); }}
  th {{ background:#f0f4f8; font-size:12px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); }}
  td.rank {{ color:var(--muted); }}
  td.score b {{ background:var(--accent); color:#fff; padding:2px 9px; border-radius:20px; font-size:13px; }}
  td.firm {{ font-weight:600; }}
  td.num,td.qs {{ text-align:center; }}
  td.seg {{ color:var(--muted); font-size:12.5px; }}
  tr.out-icp {{ opacity:.5; }}
  .table-scroll {{ overflow-x:auto; }}
  .method {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  .method .box {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px 20px; }}
  .method h3 {{ margin:0 0 10px; font-size:15px; }}
  .method table {{ border:none; }} .method td {{ border-bottom:1px solid var(--line); padding:6px 4px; }}
  .method td:last-child {{ text-align:right; font-variant-numeric:tabular-nums; color:var(--accent); font-weight:600; }}
  .brief {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:20px 22px; margin-bottom:18px; }}
  .brief-head {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; }}
  .brief-firm {{ font-size:18px; font-weight:700; }}
  .brief-sub {{ color:var(--muted); font-size:13px; margin-top:2px; }}
  .brief-score {{ font-size:30px; font-weight:800; color:var(--accent); white-space:nowrap; }}
  .brief-score span {{ font-size:14px; color:var(--muted); font-weight:500; }}
  .brief-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:16px 0 12px; }}
  .brief-grid > div {{ font-size:14px; }}
  .k {{ display:block; font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin-bottom:2px; }}
  .score-chips {{ margin:6px 0 14px; }}
  .chip {{ display:inline-block; background:var(--chip); border:1px solid var(--line); border-radius:20px;
           padding:3px 10px; font-size:12px; margin:0 6px 6px 0; }}
  .reason,.qterms,.target {{ font-size:13.5px; margin-bottom:12px; padding:10px 12px; background:#fafcfe;
            border:1px solid var(--line); border-radius:8px; }}
  .email {{ border-top:1px dashed var(--line); padding-top:12px; }}
  .email summary {{ cursor:pointer; font-weight:600; color:var(--accent); }}
  .email-subj {{ margin:12px 0 8px; font-size:14px; }}
  .email-body {{ background:#fbfdff; border:1px solid var(--line); border-radius:8px; padding:16px 18px;
                 font-size:13.5px; color:#24333f; }}
  .honesty {{ background:#fff8f0; border:1px solid #f0d9bd; border-radius:10px; padding:18px 22px; }}
  .honesty li {{ margin-bottom:7px; }}
  footer {{ color:var(--muted); font-size:13px; padding:30px 0 60px; }}
  a {{ color:var(--accent); }}
  @media (max-width:720px) {{ .method,.brief-grid {{ grid-template-columns:1fr 1fr; }} header h1{{font-size:26px;}} }}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <span class="tag">GTM Signal Engine · unsolicited spec build for Atlas Compliance</span>
    <h1>FDA enforcement, turned into a ranked outreach queue.</h1>
    <p>Atlas sells compliance intelligence to pharma quality teams. The strongest moment to reach one is the week it takes an FDA enforcement action. This engine pulls real FDA recall data, scores every firm for buying-trigger intensity, and drafts the outreach — grounded only in what the FDA actually filed.</p>
    <div class="stats">
      <div class="stat"><b>{raw['total_available']:,}</b><span>FDA drug-enforcement records available</span></div>
      <div class="stat"><b>{len(raw['records']):,}</b><span>most-recent pulled &amp; scored</span></div>
      <div class="stat"><b>{scored['firms_scored']}</b><span>distinct firms ranked</span></div>
      <div class="stat"><b>{n_classI}</b><span>with a Class I event</span></div>
      <div class="stat"><b>{india}</b><span>India-based (Atlas's 2nd named segment)</span></div>
    </div>
    <p style="margin-top:22px;padding:14px 16px;border-left:3px solid currentColor;opacity:.72;font-size:13.5px;line-height:1.6;">
      <b>Unsolicited spec work &mdash; no affiliation.</b> I built this on my own initiative ahead of an
      interview with Atlas. I have never been engaged by Atlas and have no access to any Atlas system,
      account, or internal data. Everything here comes from two public sources only: the openFDA
      enforcement API and Atlas&#39;s own public website. Nothing here is work performed for a client.
    </p>
  </div>
</header>

<section class="wrap">
  <h2>The thesis</h2>
  <div class="thesis">
    <p><b>A pharma firm's FDA enforcement action is a buying trigger for Atlas.</b> When a manufacturer files a Class I/II recall for a cGMP, sterility, or stability failure, its quality/compliance team is — that week — living the exact problem Atlas's platform (searchable 483s, EIRs, Warning Letters, peer benchmarking, investigator trends) is built to solve.</p>
    <p>This mirrors Atlas's own product logic: enforcement data is the signal. The same data that powers the product can power the <i>go-to-market</i> — an inbound-quality outbound queue where every account is contacted <i>because</i> the data says they're in acute, current pain, not because they fit a static firmographic.</p>
    <p>Data anchor date: <b>{scored['anchor_date']}</b> · Source: <a href="https://open.fda.gov/apis/drug/enforcement/">openFDA drug/enforcement</a> (public, no key). Fetched {esc(raw['fetched_at'])}.</p>
  </div>
</section>

<section class="wrap">
  <h2>How the score works</h2>
  <p class="lede">Firms are scored 0–100 on how strong a buying trigger their current enforcement situation is — not a quality verdict on the company. Every input maps to a real FDA field, weights disclosed.</p>
  <div class="method">
    <div class="box">
      <h3>Weights (max 100)</h3>
      <table>
        <tr><td>Severity — worst classification (I / II / III)</td><td>40 / 25 / 10</td></tr>
        <tr><td>Recency — most recent event (&lt;30 / &lt;90 / &lt;180d)</td><td>25 / 18 / 10</td></tr>
        <tr><td>Systemic — distinct FDA events (10+ / 4–9 / 2–3)</td><td>20 / 14 / 8</td></tr>
        <tr><td>Quality-system reason flag (cGMP/sterility/impurity…)</td><td>+10</td></tr>
        <tr><td>Any event still Ongoing</td><td>+5</td></tr>
      </table>
    </div>
    <div class="box">
      <h3>Why these, specifically</h3>
      <p style="font-size:13.5px;margin:0 0 8px;"><b>Distinct events, not recall lines.</b> One recall spans many NDCs/lots; counting lines would punish SKU breadth, not risk. Events is the honest count of separate FDA actions.</p>
      <p style="font-size:13.5px;margin:0;"><b>The quality-system flag</b> is what separates a manufacturer's cGMP failure (Atlas's core ICP — a quality-system problem that maps to 483 patterns) from a distributor's labeling recall (weak fit). Matched against FDA's own reason text, shown per firm below.</p>
    </div>
  </div>
</section>

<section class="wrap">
  <h2>Ranked account queue — top 25</h2>
  <p class="lede">Sorted by Atlas-fit score. Dimmed rows fall outside Atlas's two named ICP segments (US / India). This is what an SDR would work top-down.</p>
  <div class="table-scroll">
  <table>
    <thead><tr><th>#</th><th>Score</th><th>Firm</th><th>Worst class</th><th>Events</th><th>Recent</th><th>Qual-sys</th><th>Segment</th></tr></thead>
    <tbody>{leaderboard_rows(firms)}</tbody>
  </table>
  </div>
</section>

<section class="wrap">
  <h2>Compliance distress briefs — top 8 in-ICP firms</h2>
  <p class="lede">Each brief is built only from real FDA data. The outreach email maps the firm's actual recall reason to the specific Atlas module that addresses it. Emails are composed examples to spec — none are sent, no contact names are invented.</p>
  {brief_cards(briefs['briefs'])}
</section>

<section class="wrap">
  <h2>Honesty guardrails</h2>
  <div class="honesty">
    <ul>
      <li><b>Every firm, date, classification and reason is real</b>, pulled verbatim from openFDA. Nothing about the enforcement events is invented.</li>
      <li><b>No fabricated contacts.</b> Outreach targets a <i>role</i> (the title that owns the pain), never a made-up person or email address — inventing those would be fabrication, not enrichment.</li>
      <li><b>No email is sent.</b> The drafts are composed examples written to a spec, to show the message the signal produces.</li>
      <li><b>Scope, stated plainly:</b> openFDA exposes <i>recalls</i> — one enforcement type. Form 483s and Warning Letters (Atlas's fuller corpus) are not in this free feed. This engine detects one signal well rather than pretending to cover all three.</li>
      <li><b>Atlas's own product claims in the drafted emails are quoted, not verified by me.</b> The corpus sizes (100,000+ observations, 30,000+ 483s/EIRs, 11,800+ Warning Letters), the pricing comparison and the customer names are taken verbatim from atlas-compliance.ai as published, checked 2026-08-23. Unlike the FDA figures on this page &mdash; which carry a fetch timestamp and are reproducible from the API &mdash; I have no way to independently confirm Atlas's marketing numbers, and this page does not assert them as fact.</li>
      <li><b>The score is a buying-trigger score, not a quality verdict.</b> A high score means "acute, current pain — Atlas's best moment to help," not "bad company." Several firms here (e.g. Cipla, Zydus) are <b>named publicly as customers on Atlas's own website</b> — that public listing is the only basis for saying so; I have no visibility into Atlas's real account list. The engine has no customer-list logic and does not detect this — a human dedupes against CRM before anything is sent.</li>
    </ul>
  </div>
</section>

<footer class="wrap">
  Built by Aditya Chouhan as a targeted GTM artifact for Atlas Compliance · Pipeline: openFDA → score → brief → draft, all real data, no API keys ·
  <a href="https://open.fda.gov/apis/drug/enforcement/">Data source</a>
</footer>
</body>
</html>"""

    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(page)
    print(f"Wrote index.html ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
