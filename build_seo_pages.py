#!/usr/bin/env python3
"""Generate crawlable college-football landing, rankings and matchup pages."""
from __future__ import annotations
import html, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data"
BASE="https://matchlab.parlaycalculator.bet"

def slug(s):
    s=s.lower().replace("&"," and ")
    s=re.sub(r"[^a-z0-9]+","-",s).strip("-")
    return s

def esc(v):
    return html.escape(str(v if v is not None else "—"))

def strength(p):
    if not p: return "FBS strength unavailable"
    rank=p.get("national_strength_rank")
    score=p.get("strength_score")
    tier=p.get("strength_tier")
    ap=p.get("ap_rank")
    bits=[]
    if ap: bits.append(f"AP #{ap}")
    if rank: bits.append(f"Strength Rank #{rank}")
    if score is not None: bits.append(f"Team Strength {score}/100{(' · '+tier) if tier else ''}")
    return " · ".join(bits) or "FBS strength unavailable"

def page_shell(title,description,canonical,body):
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{esc(canonical)}">
<style>
body{{margin:0;background:#090909;color:#f5f5f5;font-family:Inter,Arial,sans-serif;line-height:1.55}}
main{{max-width:1050px;margin:auto;padding:34px 20px 70px}}
a{{color:#fff}} .eyebrow{{font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;color:#9b9b9b;font-weight:800}}
h1{{font-size:clamp(2rem,5vw,4.2rem);line-height:1.02;margin:.3rem 0 1rem}} h2{{margin-top:2rem}}
.card,.team{{border:1px solid #272727;background:#111;border-radius:16px;padding:18px}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}} .meta{{color:#b8b8b8}}
.metrics{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:14px}}
.metric{{border:1px solid #222;border-radius:12px;padding:12px;background:#0d0d0d}} .metric b{{display:block;font-size:1.25rem}}
.cta{{display:inline-block;margin-top:18px;padding:12px 16px;border-radius:10px;background:#fff;color:#111;text-decoration:none;font-weight:900}}
nav{{margin-bottom:30px;font-weight:800}} nav a{{margin-right:16px}}
@media(max-width:700px){{.grid,.metrics{{grid-template-columns:1fr}}}}
</style>
</head><body><main><nav><a href="{BASE}/">CFB Match Lab</a><a href="{BASE}/college-football-team-strength-rankings/">College Football Team Strength</a><a href="https://parlaycalculator.bet/">ParlayCalculator.bet</a></nav>{body}</main></body></html>"""

def matchup_body(g):
    away=g.get("away"); home=g.get("home")
    ap=g.get("away_profile") or {}; hp=g.get("home_profile") or {}
    result=g.get("result")
    final=""
    if result:
        final=f"""<section class="card"><p class="eyebrow">FINAL RESULT</p><h2>{esc(away)} {esc(result.get('away_points'))}, {esc(home)} {esc(result.get('home_points'))}</h2><p class="meta">ATS: {esc(result.get('ats') or 'Unavailable')} · Total: {esc(result.get('total') or 'Unavailable')}</p></section>"""
    metrics=lambda p: f"""<div class="metrics">
      <div class="metric"><span>Strength Rank</span><b>#{esc(p.get('national_strength_rank'))}</b></div>
      <div class="metric"><span>Team Strength</span><b>{esc(p.get('strength_score'))}/100</b></div>
      <div class="metric"><span>Schedule Strength</span><b>{esc(p.get('schedule_strength_score'))}</b></div>
    </div>"""
    return f"""<p class="eyebrow">CFB MATCH LAB · COLLEGE FOOTBALL MATCHUP ARCHIVE</p>
<h1>{esc(away)} at {esc(home)} — {esc(g.get('season'))}</h1>
<p class="meta">Week {esc(g.get('week'))} · {esc(g.get('start_date'))}</p>
<p>This permanent CFB Match Lab page preserves the pregame college football context for this matchup. Ratings below reflect the information available before kickoff.</p>
<div class="grid">
<section class="team"><h2>{esc(away)}</h2><p>{esc(strength(ap))}</p>{metrics(ap)}</section>
<section class="team"><h2>{esc(home)}</h2><p>{esc(strength(hp))}</p>{metrics(hp)}</section>
</div>
<section class="card"><h2>Pregame market</h2><p>Spread: {esc(g.get('spread'))} · O/U: {esc(g.get('over_under'))} · {esc(home)} ML: {esc(g.get('home_moneyline'))} · {esc(away)} ML: {esc(g.get('away_moneyline'))}</p></section>
{final}
<a class="cta" href="{BASE}/?mode=history&game={quote(str(g.get('game_id')))}">Open this game in CFB Match Lab</a>
<p class="meta">Inside CFB Match Lab, choose Spread, Moneyline or O/U Total to compare this game with the 10 closest historical college football matchups using pregame-only data.</p>"""

def main():
    now=datetime.now(timezone.utc)
    year=now.year
    historical_path=DATA/"historical"/f"{year}.json"
    upcoming_path=DATA/"upcoming.json"
    historical=json.loads(historical_path.read_text()).get("games",[]) if historical_path.exists() else []
    upcoming=json.loads(upcoming_path.read_text()).get("games",[]) if upcoming_path.exists() else []

    # Main CFB matchup-tool landing page.
    d=ROOT/"college-football-matchup-tool"; d.mkdir(exist_ok=True)
    body=f"""<p class="eyebrow">CFB MATCH LAB</p><h1>College Football Matchup Research Tool</h1>
<p>CFB Match Lab compares upcoming and past college football games with historically similar pregame situations. Research Team Strength, schedule quality, season-to-date form, market lines and advanced metrics, then view the 10 closest historical matchup profiles.</p>
<a class="cta" href="{BASE}/">Use CFB Match Lab</a>
<h2>What you can research</h2><div class="grid"><div class="card"><b>Upcoming college football games</b><p>Compare the next seven days of FBS matchups.</p></div><div class="card"><b>Past college football games</b><p>Reopen the exact pregame context for completed games.</p></div><div class="card"><b>Historical matchup comparisons</b><p>Find the 10 closest prior games by market, strength, form and advanced profile.</p></div><div class="card"><b>College football Team Strength</b><p>Track compounded weekly movement from preseason based on opponent quality and game performance.</p></div></div>"""
    (d/"index.html").write_text(page_shell("CFB Match Lab | College Football Matchup Research Tool","Research upcoming and past college football matchups with CFB Match Lab, Team Strength, schedule quality, advanced metrics and historically similar games.",f"{BASE}/college-football-matchup-tool/",body),encoding="utf-8")

    # Current Team Strength rankings page from upcoming profiles.
    team_rows={}
    for g in upcoming:
        for side in ("home","away"):
            team=g.get(side); p=g.get(f"{side}_profile") or {}
            if team and p.get("national_strength_rank"):
                team_rows[team]=p
    ranked=sorted(team_rows.items(),key=lambda x:(x[1].get("national_strength_rank") or 999,x[0]))
    rd=ROOT/"college-football-team-strength-rankings";rd.mkdir(exist_ok=True)
    rows="".join(f"<div class='card'><b>#{esc(p.get('national_strength_rank'))} {esc(t)}</b><p class='meta'>Team Strength {esc(p.get('strength_score'))}/100 · {esc(p.get('strength_tier'))} · Schedule Strength {esc(p.get('schedule_strength_score'))}</p></div>" for t,p in ranked)
    body=f"""<p class="eyebrow">CFB MATCH LAB DATA</p><h1>College Football Team Strength Rankings</h1>
<p>Current CFB Match Lab power rankings. Teams begin from a preseason baseline and move week by week based on opponent quality and game performance. The rating compounds through the season and is pregame-safe.</p><div class="grid">{rows}</div><a class="cta" href="{BASE}/">Research matchups in CFB Match Lab</a>"""
    (rd/"index.html").write_text(page_shell("College Football Team Strength Rankings | CFB Match Lab","Current college football Team Strength rankings from CFB Match Lab, updated with compounded weekly movement based on opponent quality and game performance.",f"{BASE}/college-football-team-strength-rankings/",body),encoding="utf-8")

    # Permanent current-season matchup pages.
    matchup_root=ROOT/"college-football"/"matchups"; matchup_root.mkdir(parents=True,exist_ok=True)
    seen={}
    for g in historical+upcoming:
        if not g.get("home") or not g.get("away"): continue
        seen[str(g.get("game_id"))]=g
    urls=[]
    for g in seen.values():
        s=f"{slug(g['away'])}-at-{slug(g['home'])}-{g.get('season')}-week-{g.get('week')}"
        out=matchup_root/s; out.mkdir(parents=True,exist_ok=True)
        title=f"{g['away']} at {g['home']} {g.get('season')} | CFB Match Lab"
        desc=f"College football matchup research for {g['away']} at {g['home']}: pregame Team Strength, schedule context, market lines and historical comparison access."
        url=f"{BASE}/college-football/matchups/{s}/"
        (out/"index.html").write_text(page_shell(title,desc,url,matchup_body(g)),encoding="utf-8")
        urls.append(url)

    # Sitemap contains the core landing pages plus current-season permanent matchup URLs.
    sm=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url,priority,freq in [
        (f"{BASE}/","1.0","daily"),
        (f"{BASE}/college-football-matchup-tool/","0.9","weekly"),
        (f"{BASE}/college-football-team-strength-rankings/","0.9","daily"),
    ]:
        sm.append(f"<url><loc>{url}</loc><lastmod>{now.date()}</lastmod><changefreq>{freq}</changefreq><priority>{priority}</priority></url>")
    for url in sorted(urls):
        sm.append(f"<url><loc>{url}</loc><lastmod>{now.date()}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>")
    sm.append("</urlset>")
    (ROOT/"sitemap.xml").write_text("\n".join(sm),encoding="utf-8")
    print(f"Built {len(urls)} current-season college football matchup pages")

if __name__=="__main__":
    main()
