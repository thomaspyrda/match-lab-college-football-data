# Build trigger: ranking help text updated 2026-10-02
#!/usr/bin/env python3
"""Generate crawlable CFB Match Lab landing, ranking, season and matchup pages."""
from __future__ import annotations
import html, json, re, shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data"
BASE="https://matchlab.parlaycalculator.bet"
FIRST_SEASON=2015

ADVANCED_LABELS=[
    ("offensive_efficiency","Offensive Efficiency"),
    ("defensive_efficiency","Defensive Efficiency"),
    ("rushing_success","Rushing Success"),
    ("passing_success","Passing Success"),
    ("explosiveness","Explosiveness"),
    ("havoc","Havoc"),
    ("finishing_drives","Finishing Drives"),
]

def slug(s):
    s=s.lower().replace("&"," and ")
    return re.sub(r"[^a-z0-9]+","-",s).strip("-")

def esc(v):
    return html.escape(str(v if v is not None else "—"))

def strength(p):
    if not p:
        return "FBS strength unavailable"
    bits=[]
    if p.get("ap_rank"):
        bits.append(f"AP #{p['ap_rank']}")
    if p.get("national_strength_rank"):
        bits.append(f"Strength Rank #{p['national_strength_rank']}")
    if p.get("strength_score") is not None:
        tier=p.get("strength_tier")
        bits.append(f"Team Strength {p['strength_score']}/100{(' · '+tier) if tier else ''}")
    return " · ".join(bits) or "FBS strength unavailable"

def usable_profile(p):
    if not p:
        return False
    recent=(p.get("recent_form") or {}).get("games") or 0
    advanced=p.get("advanced") or {}
    return recent >= 1 and (advanced.get("games_played") or 0) >= 1 and (advanced.get("metrics_available") or 0) >= 1

def eligible_completed(g):
    return bool(
        g.get("result") is not None
        and usable_profile(g.get("home_profile"))
        and usable_profile(g.get("away_profile"))
    )

def indexable_current(g, upcoming_ids):
    if g.get("result") is not None:
        return eligible_completed(g)
    return (
        str(g.get("game_id")) in upcoming_ids
        and usable_profile(g.get("home_profile"))
        and usable_profile(g.get("away_profile"))
    )

def page_shell(title,description,canonical,body):
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{esc(canonical)}">
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@700;800;900&family=Outfit:wght@400;500;600;700;800;900&display=swap');
:root{{--bg:#0f0f0f;--p:#1f1f1f;--line:#303030;--text:#f4f4f4;--muted:#9d9d9d;--green:#00ff41;--font:'Outfit',system-ui,sans-serif}}
*{{box-sizing:border-box}}
body{{margin:0;background:radial-gradient(circle at 75% 0,rgba(0,255,65,.08),transparent 30%),var(--bg);color:var(--text);font:15px/1.5 var(--font);-webkit-font-smoothing:antialiased}}
main{{max-width:1180px;margin:auto;padding:34px 22px 70px}}
a{{color:#fff}} .eyebrow{{font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;color:#9b9b9b;font-weight:800}}
h1{{font-family:'DM Sans',system-ui,sans-serif;font-weight:900;font-size:clamp(40px,6vw,66px);line-height:1.02;margin:.3rem 0 1rem}}
h2,h3{{font-family:'DM Sans',system-ui,sans-serif;font-weight:800}}
h2{{margin-top:2rem}}
.card,.team{{border:1px solid #272727;background:#111;border-radius:16px;padding:18px}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}} .meta{{color:#b8b8b8}}
.metrics{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:14px}}
.metric{{border:1px solid #222;border-radius:12px;padding:12px;background:#0d0d0d}} .metric b{{display:block;font-size:1.25rem}}
.cta{{display:inline-block;margin-top:18px;padding:12px 16px;border-radius:10px;background:#fff;color:#111;text-decoration:none;font-weight:900}}
.site-header{{position:relative;z-index:20;min-height:78px;border-bottom:1px solid var(--line);background:rgba(20,20,20,.94);backdrop-filter:blur(14px)}}
.header-inner{{position:relative;max-width:1280px;min-height:78px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:28px;padding:8px 22px}}
.betwise-brand{{flex:0 0 auto;width:60px;height:60px;display:grid;place-items:center;overflow:hidden;border-radius:12px;background:#000;text-decoration:none;transition:opacity .2s ease,box-shadow .2s ease}}
.betwise-brand:hover,.betwise-brand:focus-visible{{opacity:.86;box-shadow:0 0 0 1px rgba(0,255,65,.5)}}
.betwise-brand img{{width:100%;height:100%;display:block;object-fit:contain}}
.site-nav{{display:flex;align-items:center;gap:4px;padding:5px;border:1px solid var(--line);border-radius:999px;background:rgba(31,31,31,.78);margin:0}}
.site-nav a,.mobile-menu nav a{{color:#b7b7b7;text-decoration:none;text-transform:uppercase;font-size:12px;font-weight:800;letter-spacing:.07em;transition:color .2s ease,background .2s ease}}
.site-nav a{{padding:10px 16px;border-radius:999px;white-space:nowrap}}
.site-nav a:hover,.site-nav a:focus-visible,.site-nav a.active,.mobile-menu nav a:hover,.mobile-menu nav a:focus-visible,.mobile-menu nav a.active{{color:var(--green);background:rgba(0,255,65,.08)}}
.mobile-menu{{display:none;position:relative}}
.mobile-menu summary{{min-width:74px;min-height:44px;display:grid;place-items:center;border:1px solid var(--line);border-radius:999px;background:var(--p);color:var(--text);font-size:12px;font-weight:800;letter-spacing:.08em;list-style:none;text-transform:uppercase;cursor:pointer}}
.mobile-menu summary::-webkit-details-marker{{display:none}}
.mobile-menu[open] summary{{border-color:rgba(0,255,65,.55);color:var(--green)}}
.mobile-menu nav{{position:absolute;top:calc(100% + 10px);right:0;width:min(270px,calc(100vw - 44px));display:grid;gap:4px;padding:8px;border:1px solid var(--line);border-radius:14px;background:#181818;box-shadow:0 20px 50px rgba(0,0,0,.48)}}
.mobile-menu nav a{{min-height:44px;display:flex;align-items:center;padding:11px 13px;border-radius:9px}}
.rank-hero{{margin:16px 0 22px;border:1px solid #1f6f34;border-radius:18px;overflow:hidden;background:#0d0d0d}}
.rank-hero img{{display:block;width:100%;height:auto;aspect-ratio:3.15/1;object-fit:cover}}
.rank-tabs{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:14px 0 20px}}
.rank-tabs a{{display:flex;align-items:center;justify-content:center;min-height:46px;border:1px solid #2b2b2b;background:#111;border-radius:12px;padding:10px 12px;text-decoration:none;font-size:.9rem;font-weight:800;text-align:center}}
.rank-tabs a.active{{border-color:#00ff41;color:#00ff41;background:#0d170f;box-shadow:0 0 0 1px rgba(0,255,65,.08)}}
.rank-tabs a:hover,.rank-tabs a:focus-visible{{border-color:#555;background:#161616}}
.rank-tabs-label{{margin:18px 0 6px;color:#9d9d9d;font-size:.72rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase}}

.archive-list{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
.archive-list a{{border:1px solid #272727;background:#111;border-radius:14px;padding:14px;text-decoration:none}}
.page-intro{{max-width:860px;color:#c6c6c6;margin:0 0 16px}}
.data-links{{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 18px}}
.data-links a{{border:1px solid #272727;background:#111;border-radius:999px;padding:7px 11px;text-decoration:none;font-size:.84rem}}
.data-table-wrap{{overflow:hidden;border:1px solid #272727;border-radius:16px;background:#111}}
.data-table{{width:100%;border-collapse:collapse;table-layout:fixed}}
.data-table th,.data-table td{{padding:10px 7px;border-bottom:1px solid #242424;text-align:left;vertical-align:middle}}
.data-table th{{font-family:'DM Sans',system-ui,sans-serif;font-size:.67rem;line-height:1.18;letter-spacing:.025em;text-transform:uppercase;color:#aaa;background:#0d0d0d;position:sticky;top:0;white-space:normal}}
.data-table td{{font-size:.84rem;line-height:1.2;white-space:normal;overflow-wrap:anywhere}}
.data-table tr:last-child td{{border-bottom:0}}
.data-table td:first-child{{font-weight:800}}
.rank-num{{font-family:'DM Sans',system-ui,sans-serif;font-weight:900;font-size:1.05rem}}
.help-wrap{{display:inline-flex;align-items:center;gap:4px;position:relative;max-width:100%}}
.help-btn{{appearance:none;-webkit-appearance:none;border:1px solid #555;background:#171717;color:#d0d0d0;border-radius:50%;width:16px;height:16px;min-width:16px;padding:0;font:800 10px/14px 'DM Sans',sans-serif;cursor:pointer}}
.help-btn:hover,.help-btn:focus-visible{{color:#fff;border-color:#8d8d8d;outline:none}}
.help-pop{{display:none;position:absolute;z-index:100;top:22px;left:0;width:250px;max-width:70vw;padding:10px 11px;border:1px solid #3a3a3a;border-radius:10px;background:#181818;color:#eee;font:500 12px/1.4 'Outfit',sans-serif;text-transform:none;letter-spacing:0;white-space:normal;box-shadow:0 10px 28px rgba(0,0,0,.48)}}
.help-wrap.open .help-pop{{display:block}}
.data-table th:nth-child(1),.data-table td:nth-child(1){{width:6%}}
.data-table th:nth-child(2),.data-table td:nth-child(2){{width:15%}}
.data-table th:nth-child(3),.data-table td:nth-child(3){{width:8%}}
.note{{border-left:3px solid #00ff41;padding:10px 14px;background:#101410;color:#d7d7d7}}
@media(max-width:900px){{
 .grid,.metrics,.archive-list{{grid-template-columns:1fr}}
 .site-nav{{display:none}}
 .mobile-menu{{display:block}}
 .header-inner{{padding-left:12px;padding-right:12px}}
 main{{padding-left:12px;padding-right:12px}}
 .data-table th,.data-table td{{padding:8px 4px}}
 .data-table th{{font-size:.58rem;letter-spacing:0}}
 .data-table td{{font-size:.72rem}}
 .help-btn{{width:14px;height:14px;min-width:14px;font-size:9px;line-height:12px}}
}}
@media(max-width:620px){{
 h1{{font-size:clamp(34px,10vw,48px)}}
 .rank-tabs{{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}
 .rank-tabs a{{min-height:42px;padding:8px 9px;font-size:.78rem}}
 .data-table th,.data-table td{{padding:7px 3px}}
 .data-table th{{font-size:.5rem}}
 .data-table td{{font-size:.62rem}}
 .help-pop{{position:fixed;left:12px;right:auto;top:auto;width:min(280px,calc(100vw - 24px));max-width:none;transform:none}}
}}
</style>
</head><body>
<header class="site-header">
  <div class="header-inner">
    <a class="betwise-brand" href="https://parlaycalculator.bet/" aria-label="BetWise and ParlayCalculator.bet home">
      <img src="{BASE}/assets/betwise-logo.png" alt="BetWise Sports Picks" width="240" height="240">
    </a>
    <nav class="site-nav" aria-label="Primary navigation">
      <a href="https://parlaycalculator.bet/betwise">Why BetWise?</a>
      <a class="active" href="{BASE}/" aria-current="page">CFB Match Lab</a>
      <a href="https://nfl.parlaycalculator.bet/">NFL Dashboard</a>
      <a href="https://parlaycalculator.bet/#calculator">Parlay Calculator</a>
      <a href="https://parlaycalculator.bet/resources">Resources</a>
    </nav>
    <details class="mobile-menu">
      <summary aria-label="Open navigation menu">Menu</summary>
      <nav aria-label="Mobile navigation">
        <a href="https://parlaycalculator.bet/betwise">Why BetWise?</a>
        <a class="active" href="{BASE}/" aria-current="page">CFB Match Lab</a>
        <a href="https://nfl.parlaycalculator.bet/">NFL Dashboard</a>
        <a href="https://parlaycalculator.bet/#calculator">Parlay Calculator</a>
        <a href="https://parlaycalculator.bet/resources">Resources</a>
      </nav>
    </details>
  </div>
</header>
<main>{body}</main>
<script>
document.addEventListener('click',function(e){{
 const btn=e.target.closest('.help-btn');
 document.querySelectorAll('.help-wrap.open').forEach(w=>{{if(!btn||w!==btn.closest('.help-wrap'))w.classList.remove('open')}});
 if(btn){{
   e.preventDefault();e.stopPropagation();
   const w=btn.closest('.help-wrap');
   w.classList.toggle('open');
   btn.setAttribute('aria-expanded',w.classList.contains('open')?'true':'false');
   if(w.classList.contains('open')&&window.innerWidth<=620){{
     const pop=w.querySelector('.help-pop');
     const r=btn.getBoundingClientRect();
     const width=Math.min(280,window.innerWidth-24);
     const left=Math.max(12,Math.min(window.innerWidth-width-12,r.left+r.width/2-width/2));
     pop.style.left=left+'px';
     pop.style.top=(r.bottom+8)+'px';
   }}
 }}
}});
document.addEventListener('keydown',function(e){{if(e.key==='Escape')document.querySelectorAll('.help-wrap.open').forEach(w=>w.classList.remove('open'))}});
</script></body></html>"""

def team_snapshot(name,p):
    recent=p.get("recent_form") or {}
    advanced=p.get("advanced") or {}
    top=f"""<div class="metrics">
      <div class="metric"><span>Strength Rank</span><b>#{esc(p.get('national_strength_rank'))}</b></div>
      <div class="metric"><span>Team Strength</span><b>{esc(p.get('strength_score'))}/100</b></div>
      <div class="metric"><span>Schedule Strength</span><b>{esc(p.get('schedule_strength_score'))}</b></div>
    </div>"""
    adv="".join(
        f"<div class='metric'><span>{label}</span><b>{esc(advanced.get(key))}</b></div>"
        for key,label in ADVANCED_LABELS
    )
    form=(
        f"{recent.get('wins',0)}-{recent.get('losses',0)} through {recent.get('games',0)} prior games · "
        f"{esc(recent.get('avg_points'))} PPG · {esc(recent.get('avg_allowed'))} allowed"
    )
    return f"""<section class="team"><h2>{esc(name)}</h2><p>{esc(strength(p))}</p>{top}
<h3>Pregame advanced profile</h3><div class="metrics">{adv}</div>
<p class="meta">{form}</p></section>"""

def matchup_body(g,season_url):
    away=g.get("away"); home=g.get("home")
    ap=g.get("away_profile") or {}; hp=g.get("home_profile") or {}
    result=g.get("result")
    final=""
    if result:
        final=f"""<section class="card"><p class="eyebrow">FINAL RESULT</p><h2>{esc(away)} {esc(result.get('away_points'))}, {esc(home)} {esc(result.get('home_points'))}</h2><p class="meta">ATS: {esc(result.get('ats') or 'Unavailable')} · Total result: {esc(result.get('total') or 'Unavailable')}</p></section>"""
    context=[]
    if g.get("conference_game") is True:
        context.append("Conference game")
    elif g.get("conference_game") is False:
        context.append("Non-conference game")
    if g.get("neutral_site"):
        context.append("Neutral site")
    if g.get("favorite_side"):
        fav=home if g.get("favorite_side")=="home" else away
        context.append(f"{fav} entered as the listed favorite")
    context_text=" · ".join(context) if context else "Pregame context preserved from the historical dataset"
    return f"""<p class="eyebrow">CFB MATCH LAB · COLLEGE FOOTBALL MATCHUP ARCHIVE</p>
<h1>{esc(away)} at {esc(home)} — {esc(g.get('season'))}</h1>
<p class="meta">Week {esc(g.get('week'))} · {esc(g.get('start_date'))}</p>
<p>This archive page preserves the information available before kickoff so the matchup can be researched without using future results in its pregame profile.</p>
<p class="meta">{esc(context_text)}</p>
<div class="grid">{team_snapshot(away,ap)}{team_snapshot(home,hp)}</div>
<section class="card"><h2>Pregame market</h2><p>Spread: {esc(g.get('spread'))} · O/U: {esc(g.get('over_under'))} · {esc(home)} ML: {esc(g.get('home_moneyline'))} · {esc(away)} ML: {esc(g.get('away_moneyline'))}</p></section>
{final}
<a class="cta" href="{BASE}/?mode=history&game={quote(str(g.get('game_id')))}">Open this game in CFB Match Lab</a>
<p class="meta">Inside CFB Match Lab, choose Spread, Moneyline or O/U Total to compare this game with the 10 closest historical college football matchups using pregame-only data.</p>
<p><a href="{season_url}">Browse all eligible {esc(g.get('season'))} archived matchups</a></p>"""

def write_urlset(path,urls,lastmod):
    rows=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url,priority,freq in urls:
        rows.append(f"<url><loc>{url}</loc><lastmod>{lastmod}</lastmod><changefreq>{freq}</changefreq><priority>{priority}</priority></url>")
    rows.append("</urlset>")
    path.write_text("\n".join(rows),encoding="utf-8")


def current_rankings_data():
    p=DATA/"current_rankings.json"
    if not p.exists():
        return {"teams":[],"week":None,"through_week":None,"season":None,"generated_at":None}
    return json.loads(p.read_text(encoding="utf-8"))

COLUMN_HELP={
    "rank":"Current position in this ranking table.",
    "team":"College football team.",
    "ap":"Current AP Poll rank shown for reference only. It does not affect Match Lab ratings.",
    "strength":"Overall Team Strength combines nationally ranked offensive and defensive performance after opponent-strength adjustments. AP rank is not used.",
    "offense":"Offensive Strength is built from opponent-adjusted performance metrics, normalized against the FBS field and combined by national metric rank.",
    "defense":"Defensive Strength is built from opponent-adjusted performance metrics, normalized against the FBS field and combined by national metric rank.",
    "sos":"National strength-of-schedule rank based on opponents already faced. The lowest number represents the toughest schedule to date (#1 = toughest).",
    "raw":"Average entering Team Strength of opponents already faced. This reflects schedule quality through completed games only.",
    "strength_rank":"Current overall Team Strength rank.",
    "score":"Current unit strength score derived from opponent-adjusted performance metrics normalized against the FBS field.",
    "vs_expectation":"Season-to-date performance versus pregame expectation after accounting for opponent quality. Higher means more consistent overperformance.",
    "opp_quality":"Average entering strength of opposing units already faced; used to adjust performance for quality of competition.",
    "multiplier":"Average opponent-strength adjustment across completed games. Stronger competition increases credit; weaker competition reduces it."
    "overall_rank":"Current overall Team Strength rank.",
    "overall":"Current overall Team Strength score.",
    "record":"Current season win-loss record through completed games."
}

def ranking_tabs(active):
    items=[
        ("team","Team Strength",f"{BASE}/college-football-team-strength-rankings/"),
        ("sos","SOS Rankings",f"{BASE}/college-football-strength-of-schedule-rankings/"),
        ("offense","Offensive Strength",f"{BASE}/college-football-offensive-strength-rankings/"),
        ("defense","Defensive Strength",f"{BASE}/college-football-defensive-strength-rankings/"),
    ]
    return "<p class='rank-tabs-label'>Explore CFB Rankings</p><div class='rank-tabs' aria-label='CFB ranking categories'>"+"".join(
        f"<a href='{url}' class='{'active' if key==active else ''}'{' aria-current=\"page\"' if key==active else ''}>{label}</a>"
        for key,label,url in items
    )+"</div>"

def ranking_hero():
    return f"""<div class="rank-hero">
<img src="{BASE}/assets/betwise-cfb-vip-collage.webp" alt="College football players and mascots in a stadium collage">
</div>"""

def ranking_table(rows,columns):
    head=[]
    for key,label in columns:
        help_text=COLUMN_HELP.get(key,"Context for this statistic based on completed games to date.")
        head.append(
            f"<th><span class='help-wrap'><span>{esc(label)}</span>"
            f"<button class='help-btn' type='button' aria-label='About {esc(label)}' aria-expanded='false'>?</button>"
            f"<span class='help-pop' role='tooltip'>{esc(help_text)}</span></span></th>"
        )
    body=[]
    for idx,row in enumerate(rows,1):
        cells=[]
        for key,label in columns:
            value=row.get(key)
            if key=="rank":
                value=idx
            cells.append(f"<td data-label='{esc(label)}'>{esc(value)}</td>")
        body.append("<tr>"+"".join(cells)+"</tr>")
    return f"<div class='data-table-wrap'><table class='data-table'><thead><tr>{''.join(head)}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"

def write_live_data_pages(now):
    data=current_rankings_data()
    teams=data.get("teams") or []
    season=data.get("season") or now.year
    week=data.get("week")
    through=data.get("through_week")
    stamp=data.get("generated_at")
    snapshot_type=data.get("snapshot_type")
    context=(f"{season} season · current through completed games in Week {esc(through)}" if snapshot_type=="current_to_date" else f"{season} season · Week {esc(week)} pregame snapshot · through Week {esc(through)}")

    # Full Team Strength ranking. Overall Strength is built from the opponent-adjusted
    # Offensive Strength and Defensive Strength components in current_rankings.json.
    strength_rows=[]
    for r in teams:
        rank=r.get("overall_strength_rank")
        score=r.get("overall_strength_score")
        if rank is None or score is None:
            continue
        strength_rows.append({
            "rank":rank,
            "team":r.get("team"),
            "strength":score,
            "offense":r.get("offensive_strength"),
            "defense":r.get("defensive_strength"),
            "sos":r.get("schedule_strength_rank"),
            "ap":f"#{r.get('ap_rank')}" if r.get("ap_rank") else "—",
            "record":r.get("record") or "—",
        })
    strength_rows=sorted(strength_rows,key=lambda r:(r["rank"] or 999,r["team"]))
    d=ROOT/"college-football-team-strength-rankings"; d.mkdir(exist_ok=True)
    table=ranking_table(strength_rows,[("rank","Rank"),("team","Team"),("sos","SOS"),("strength","Team Strength"),("offense","Offense"),("defense","Defense"),("ap","AP"),("record","Record")])
    body=f"""<p class="eyebrow">CFB MATCH LAB · LIVE DATA</p><h1>{season} College Football Team Strength Rankings</h1>
<p class="page-intro">{context}. Current opponent-adjusted Team Strength rankings based on games already completed. Tap or click any <b>?</b> in the table headers for metric definitions.</p>
{ranking_tabs("team")}
{ranking_hero()}
{table}<p class="meta">Last generated: {esc(stamp)}</p>"""
    (d/"index.html").write_text(page_shell(f"{season} College Football Team Strength Rankings | CFB Match Lab",f"Current {season} college football Team Strength rankings for the full FBS field from CFB Match Lab, updated weekly using opponent quality and game performance.",f"{BASE}/college-football-team-strength-rankings/",body),encoding="utf-8")

    # Strength of Schedule.
    sos_rows=[]
    for r in teams:
        if r.get("schedule_strength_rank") is None:
            continue
        sos_rows.append({
            "rank":r.get("schedule_strength_rank"),
            "team":r.get("team"),
            "raw":r.get("schedule_strength"),
            "strength_rank":r.get("overall_strength_rank"),
            "strength":r.get("overall_strength_score"),
            "record":r.get("record") or "—",
        })
    sos_rows=sorted(sos_rows,key=lambda r:(r["rank"] or 999,r["team"]))
    d=ROOT/"college-football-strength-of-schedule-rankings"; d.mkdir(exist_ok=True)
    table=ranking_table(sos_rows,[("rank","SOS Rank"),("team","Team"),("raw","Opp Strength Avg"),("strength_rank","Team Rank"),("strength","Team Strength"),("record","Record")])
    body=f"""<p class="eyebrow">CFB MATCH LAB · LIVE DATA</p><h1>{season} College Football Strength of Schedule Rankings</h1>
<p class="page-intro">{context}. Current strength-of-schedule rankings based only on opponents already faced, not future schedule projections. Tap or click any <b>?</b> for metric definitions.</p>
{ranking_tabs("sos")}
{ranking_hero()}
{table}<p class="meta">Last generated: {esc(stamp)}</p>"""
    (d/"index.html").write_text(page_shell(f"{season} College Football Strength of Schedule Rankings | CFB Match Lab",f"Current {season} college football strength of schedule rankings based on opponent strength already faced, with full-FBS SOS percentiles from CFB Match Lab.",f"{BASE}/college-football-strength-of-schedule-rankings/",body),encoding="utf-8")

    def unit_strength_page(field,rank_field,label,slug_name,opponent_label,multiplier_field,opponent_quality_field):
        rows=[]
        for r in teams:
            score=r.get(field)
            rank=r.get(rank_field)
            if score is None or rank is None:
                continue
            rows.append({
                "rank":rank,
                "team":r.get("team"),
                "score":score,
                "ap":f"#{r.get('ap_rank')}" if r.get("ap_rank") else "—",
                "opp_quality":r.get(opponent_quality_field),
                "overall_rank":r.get("overall_strength_rank"),
                "overall":r.get("overall_strength_score"),
                "sos":r.get("schedule_strength_score"),
                "record":r.get("record") or "—",
            })
        rows=sorted(rows,key=lambda r:(r["rank"] or 999,r["team"]))
        d=ROOT/slug_name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(exist_ok=True)
        table=ranking_table(rows,[("rank","Rank"),("team","Team"),("ap","AP"),("score",label),("opp_quality",opponent_label),("overall_rank","Team Rank"),("overall","Team Strength"),("record","Record")])
        body=f"""<p class="eyebrow">CFB MATCH LAB · OPPONENT-ADJUSTED DATA</p><h1>{season} College Football {label} Rankings</h1>
<p class="page-intro">{context}. Current opponent-adjusted {label.lower()} rankings based on completed games. Tap or click any <b>?</b> in the table headers for metric definitions and context.</p>
{ranking_tabs("offense" if field=="offensive_strength" else "defense")}
{ranking_hero()}
{table}<p class="meta">Last generated: {esc(stamp)}</p>"""
        (d/"index.html").write_text(page_shell(f"{season} College Football {label} Rankings | CFB Match Lab",f"Current {season} college football {label.lower()} rankings from CFB Match Lab, adjusted for the quality of opposing units faced.",f"{BASE}/{slug_name}/",body),encoding="utf-8")

    # Remove stale efficiency pages from the deployment so Google is not offered
    # two competing concepts for the same underlying data.
    for stale in ("college-football-offensive-efficiency-rankings","college-football-defensive-efficiency-rankings"):
        p=ROOT/stale
        if p.exists():
            shutil.rmtree(p)

    unit_strength_page("offensive_strength","offensive_strength_rank","Offensive Strength","college-football-offensive-strength-rankings","Avg Defense Faced","offensive_multiplier","opponent_defensive_quality")
    unit_strength_page("defensive_strength","defensive_strength_rank","Defensive Strength","college-football-defensive-strength-rankings","Avg Offense Faced","defensive_multiplier","opponent_offensive_quality")

def main():
    now=datetime.now(timezone.utc)
    year=now.year
    upcoming_path=DATA/"upcoming.json"
    upcoming=json.loads(upcoming_path.read_text()).get("games",[]) if upcoming_path.exists() else []
    upcoming_ids={str(g.get("game_id")) for g in upcoming}

    seasons={}
    for season in range(FIRST_SEASON,year+1):
        p=DATA/"historical"/f"{season}.json"
        seasons[season]=json.loads(p.read_text()).get("games",[]) if p.exists() else []

    current_history=seasons.get(year,[])

    # Main CFB matchup-tool landing page.
    d=ROOT/"college-football-matchup-tool"; d.mkdir(exist_ok=True)
    body=f"""<p class="eyebrow">CFB MATCH LAB</p><h1>College Football Matchup Research Tool</h1>
<p>CFB Match Lab compares upcoming and past college football games with historically similar pregame situations. Research Team Strength, schedule quality, season-to-date form, market lines and advanced metrics, then view the 10 closest historical matchup profiles.</p>
<a class="cta" href="{BASE}/">Use CFB Match Lab</a>
<h2>What you can research</h2><div class="grid"><div class="card"><b>Upcoming college football games</b><p>Compare the next seven days of FBS matchups.</p></div><div class="card"><b>Past college football games</b><p>Reopen the exact pregame context for completed games.</p></div><div class="card"><b>Historical matchup comparisons</b><p>Find the 10 closest prior games by market, strength, form and advanced profile.</p></div><div class="card"><b>College football Team Strength</b><p>Track compounded weekly movement from preseason based on opponent quality and game performance.</p></div></div>"""
    (d/"index.html").write_text(page_shell("CFB Match Lab | College Football Matchup Research Tool","Research upcoming and past college football matchups with CFB Match Lab, Team Strength, schedule quality, advanced metrics and historically similar games.",f"{BASE}/college-football-matchup-tool/",body),encoding="utf-8")

    # Generate live full-FBS data pages from the current pregame snapshot.
    write_live_data_pages(now)

    # Rebuild the archive from source data so stale/thin pages disappear from deployment.
    archive_root=ROOT/"college-football"/"matchups"
    if archive_root.exists():
        shutil.rmtree(archive_root)
    archive_root.mkdir(parents=True,exist_ok=True)

    all_archive=[]
    season_sitemap_files=[]

    for season,games in seasons.items():
        if season == year:
            eligible=[g for g in games if eligible_completed(g)]
            eligible += [g for g in upcoming if indexable_current(g,upcoming_ids) and g.get("result") is None]
        else:
            eligible=[g for g in games if eligible_completed(g)]

        dedup={}
        for g in eligible:
            if g.get("home") and g.get("away"):
                dedup[str(g.get("game_id"))]=g
        eligible=list(dedup.values())

        season_url=f"{BASE}/college-football/matchups/{season}/"
        season_dir=archive_root/str(season)
        season_dir.mkdir(parents=True,exist_ok=True)
        season_links=[]

        season_urls=[(season_url,"0.8","monthly")]
        for g in sorted(eligible,key=lambda x:x.get("start_date") or ""):
            s=f"{slug(g['away'])}-at-{slug(g['home'])}-{g.get('season')}-week-{g.get('week')}"
            out=archive_root/s
            out.mkdir(parents=True,exist_ok=True)
            url=f"{BASE}/college-football/matchups/{s}/"
            title=f"{g['away']} at {g['home']} {g.get('season')} | CFB Match Lab"
            desc=f"Pregame college football matchup research for {g['away']} at {g['home']} in {g.get('season')}: Team Strength, schedule context, advanced metrics, market lines and final result."
            (out/"index.html").write_text(page_shell(title,desc,url,matchup_body(g,season_url)),encoding="utf-8")
            season_urls.append((url,"0.65","yearly" if season < year else "weekly"))
            season_links.append((g,url))

        cards="".join(
            f"<a href='{url}'><b>Week {esc(g.get('week'))}: {esc(g.get('away'))} at {esc(g.get('home'))}</b><span class='meta'> · {esc(g.get('spread'))} spread · O/U {esc(g.get('over_under'))}</span></a>"
            for g,url in reversed(season_links)
        )
        season_body=f"""<p class="eyebrow">CFB MATCH LAB · HISTORICAL ARCHIVE</p><h1>{season} College Football Matchup Archive</h1>
<p>Browse {len(season_links)} completed or research-ready college football matchups with usable pregame profiles. Every archived game keeps its Team Strength, schedule context, advanced metrics and market information tied to what was known before kickoff.</p>
<div class="archive-list">{cards}</div>"""
        (season_dir/"index.html").write_text(page_shell(f"{season} College Football Matchup Archive | CFB Match Lab",f"Browse {len(season_links)} pregame-safe {season} college football matchup pages with Team Strength, advanced metrics, market context and results.",season_url,season_body),encoding="utf-8")

        season_map_name=f"sitemap-{season}.xml"
        write_urlset(ROOT/season_map_name,season_urls,now.date())
        season_sitemap_files.append((season_map_name,season,len(season_links)))
        all_archive.extend(season_links)

    # Archive index with season-level internal links.
    season_cards="".join(
        f"<a href='{BASE}/college-football/matchups/{season}/'><b>{season} season</b><span class='meta'> · {count} eligible matchups</span></a>"
        for _,season,count in reversed(season_sitemap_files)
    )
    archive_body=f"""<p class="eyebrow">CFB MATCH LAB · COLLEGE FOOTBALL DATA</p><h1>Historical College Football Matchup Archive</h1>
<p>Explore pregame-safe matchup snapshots by season. Archive pages are included only when both teams had at least one prior completed game and usable advanced pregame profiles.</p><div class="archive-list">{season_cards}</div>"""
    (archive_root/"index.html").write_text(page_shell("Historical College Football Matchup Archive | CFB Match Lab","Browse CFB Match Lab's historical college football matchup archive from 2015 forward using pregame-safe Team Strength, advanced metrics and market context.",f"{BASE}/college-football/matchups/",archive_body),encoding="utf-8")

    # Root sitemap becomes a sitemap index. Search Console can keep the same submitted URL.
    core=[
        (f"{BASE}/","1.0","daily"),
        (f"{BASE}/college-football-matchup-tool/","0.9","weekly"),
        (f"{BASE}/college-football-team-strength-rankings/","0.9","daily"),
        (f"{BASE}/college-football-strength-of-schedule-rankings/","0.9","daily"),
        (f"{BASE}/college-football-offensive-strength-rankings/","0.85","daily"),
        (f"{BASE}/college-football-defensive-strength-rankings/","0.85","daily"),
        (f"{BASE}/college-football/matchups/","0.9","weekly"),
    ]
    write_urlset(ROOT/"sitemap-core.xml",core,now.date())
    sm=['<?xml version="1.0" encoding="UTF-8"?>','<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm.append(f"<sitemap><loc>{BASE}/sitemap-core.xml</loc><lastmod>{now.date()}</lastmod></sitemap>")
    for filename,_,_ in season_sitemap_files:
        sm.append(f"<sitemap><loc>{BASE}/{filename}</loc><lastmod>{now.date()}</lastmod></sitemap>")
    sm.append("</sitemapindex>")
    (ROOT/"sitemap.xml").write_text("\n".join(sm),encoding="utf-8")

    print(f"Built {len(all_archive)} eligible matchup pages across {len(season_sitemap_files)} seasons")
    for filename,season,count in season_sitemap_files:
        print(f"{season}: {count} matchup pages -> {filename}")

if __name__=="__main__":
    main()
