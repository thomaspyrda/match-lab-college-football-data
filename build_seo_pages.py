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
body{{margin:0;background:#090909;color:#f5f5f5;font-family:'Outfit',system-ui,sans-serif;font-size:15px;line-height:1.5}}
main{{max-width:1180px;margin:auto;padding:34px 20px 70px}}
a{{color:#fff}} .eyebrow{{font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;color:#9b9b9b;font-weight:800}}
h1{{font-family:'DM Sans',system-ui,sans-serif;font-weight:900;font-size:clamp(40px,6vw,66px);line-height:1.02;margin:.3rem 0 1rem}}
h2,h3{{font-family:'DM Sans',system-ui,sans-serif;font-weight:800}}
h2{{margin-top:2rem}}
.card,.team{{border:1px solid #272727;background:#111;border-radius:16px;padding:18px}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}} .meta{{color:#b8b8b8}}
.metrics{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:14px}}
.metric{{border:1px solid #222;border-radius:12px;padding:12px;background:#0d0d0d}} .metric b{{display:block;font-size:1.25rem}}
.cta{{display:inline-block;margin-top:18px;padding:12px 16px;border-radius:10px;background:#fff;color:#111;text-decoration:none;font-weight:900}}
nav{{margin-bottom:30px;font-weight:800;display:flex;gap:16px;flex-wrap:wrap}}
nav a{{text-decoration:none}}
.archive-list{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
.archive-list a{{border:1px solid #272727;background:#111;border-radius:14px;padding:14px;text-decoration:none}}
.data-table-wrap{{overflow-x:auto;border:1px solid #272727;border-radius:16px;background:#111}}
.data-table{{width:100%;border-collapse:collapse;min-width:760px}}
.data-table th,.data-table td{{padding:12px 14px;border-bottom:1px solid #242424;text-align:left;white-space:nowrap}}
.data-table th{{font-family:'DM Sans',system-ui,sans-serif;font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:#aaa;background:#0d0d0d;position:sticky;top:0}}
.data-table tr:last-child td{{border-bottom:0}}
.data-table td:first-child{{font-weight:800}}
.rank-num{{font-family:'DM Sans',system-ui,sans-serif;font-weight:900;font-size:1.05rem}}
.data-links{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:20px 0}}
.data-links a{{border:1px solid #272727;background:#111;border-radius:14px;padding:16px;text-decoration:none}}
.note{{border-left:3px solid #00ff41;padding:10px 14px;background:#101410;color:#d7d7d7}}
@media(max-width:800px){{.grid,.metrics,.archive-list,.data-links{{grid-template-columns:1fr}}}}
</style>
</head><body><main><nav><a href="{BASE}/">CFB Match Lab</a><a href="{BASE}/college-football-matchup-tool/">Matchup Research</a><a href="{BASE}/college-football-team-strength-rankings/">Team Strength</a><a href="{BASE}/college-football-strength-of-schedule-rankings/">SOS Rankings</a><a href="{BASE}/college-football-offensive-strength-rankings/">Offensive Strength</a><a href="{BASE}/college-football-defensive-strength-rankings/">Defensive Strength</a><a href="{BASE}/college-football/matchups/">Historical Archive</a><a href="https://parlaycalculator.bet/">ParlayCalculator.bet</a></nav>{body}</main></body></html>"""

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

def ranking_table(rows,columns):
    head="".join(f"<th>{esc(label)}</th>" for _,label in columns)
    body=[]
    for idx,row in enumerate(rows,1):
        cells=[]
        for key,_ in columns:
            value=row.get(key)
            if key=="rank":
                value=idx
            cells.append(f"<td>{esc(value)}</td>")
        body.append("<tr>"+"".join(cells)+"</tr>")
    return f"<div class='data-table-wrap'><table class='data-table'><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"

def write_live_data_pages(now):
    data=current_rankings_data()
    teams=data.get("teams") or []
    season=data.get("season") or now.year
    week=data.get("week")
    through=data.get("through_week")
    stamp=data.get("generated_at")
    context=f"{season} season · Week {esc(week)} pregame snapshot · through Week {esc(through)}"

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
            "sos":r.get("schedule_strength_score"),
            "ap":f"#{r.get('ap_rank')}" if r.get("ap_rank") else "—",
            "games":r.get("games_in_rating"),
        })
    strength_rows=sorted(strength_rows,key=lambda r:(r["rank"] or 999,r["team"]))
    d=ROOT/"college-football-team-strength-rankings"; d.mkdir(exist_ok=True)
    table=ranking_table(strength_rows,[("rank","Rank"),("team","Team"),("strength","Team Strength"),("offense","Offensive Strength"),("defense","Defensive Strength"),("sos","SOS Score"),("ap","AP Rank"),("games","Games")])
    body=f"""<p class="eyebrow">CFB MATCH LAB · LIVE DATA</p><h1>{season} College Football Team Strength Rankings</h1>
<p>{context}. CFB Match Lab Team Strength is a 50/50 combination of opponent-adjusted Offensive Strength and Defensive Strength. Each unit starts with what it has actually produced, then scales that performance by the quality of the opposing unit faced.</p>
<p class="note">Offensive Strength rewards production against stronger defenses. Defensive Strength rewards suppression against stronger offenses. Historical matchup snapshots remain pregame-safe; this live board updates as completed games enter the current dataset.</p>
<div class="data-links"><a href="{BASE}/college-football-strength-of-schedule-rankings/"><b>Strength of Schedule Rankings</b><br><span class="meta">See which teams have faced the strongest opponents.</span></a><a href="{BASE}/college-football-offensive-strength-rankings/"><b>Offensive Strength Rankings</b><br><span class="meta">Compare opponent-adjusted offensive performance.</span></a></div>
{table}<p class="meta">Last generated: {esc(stamp)}</p>"""
    (d/"index.html").write_text(page_shell(f"{season} College Football Team Strength Rankings | CFB Match Lab",f"Current {season} college football Team Strength rankings for the full FBS field from CFB Match Lab, updated weekly using opponent quality and game performance.",f"{BASE}/college-football-team-strength-rankings/",body),encoding="utf-8")

    # Strength of Schedule.
    sos_rows=[]
    for r in teams:
        if r.get("schedule_strength_score") is None:
            continue
        sos_rows.append({
            "rank":None,
            "team":r.get("team"),
            "sos":r.get("schedule_strength_score"),
            "raw":r.get("schedule_strength"),
            "strength_rank":r.get("overall_strength_rank"),
            "strength":r.get("overall_strength_score"),
            "games":r.get("games_in_rating"),
        })
    sos_rows=sorted(sos_rows,key=lambda r:(-(r["sos"] or 0),r["team"]))
    for i,r in enumerate(sos_rows,1): r["rank"]=i
    d=ROOT/"college-football-strength-of-schedule-rankings"; d.mkdir(exist_ok=True)
    table=ranking_table(sos_rows,[("rank","SOS Rank"),("team","Team"),("sos","SOS Score"),("raw","Opponent Strength Avg"),("strength_rank","Team Strength Rank"),("strength","Team Strength"),("games","Games")])
    body=f"""<p class="eyebrow">CFB MATCH LAB · LIVE DATA</p><h1>{season} College Football Strength of Schedule Rankings</h1>
<p>{context}. Schedule Strength is based on the entering CFB Match Lab strength of opponents already faced. The SOS Score converts that opponent-quality average into a 1–100 FBS percentile, where 100 represents the most difficult schedule to date.</p>
<p class="note">This is schedule difficulty already faced, not a future remaining-schedule projection.</p>
<div class="data-links"><a href="{BASE}/college-football-team-strength-rankings/"><b>Team Strength Rankings</b><br><span class="meta">Compare opponent-adjusted overall ratings.</span></a><a href="{BASE}/college-football-defensive-strength-rankings/"><b>Defensive Strength Rankings</b><br><span class="meta">Compare opponent-adjusted defensive performance.</span></a></div>
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
                "opp_quality":r.get(opponent_quality_field),
                "multiplier":r.get(multiplier_field),
                "overall_rank":r.get("overall_strength_rank"),
                "overall":r.get("overall_strength_score"),
                "sos":r.get("schedule_strength_score"),
                "games":r.get("games_in_rating"),
            })
        rows=sorted(rows,key=lambda r:(r["rank"] or 999,r["team"]))
        d=ROOT/slug_name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(exist_ok=True)
        table=ranking_table(rows,[("rank","Rank"),("team","Team"),("score",label),("opp_quality",opponent_label),("multiplier","Opponent Multiplier"),("overall_rank","Team Rank"),("overall","Team Strength"),("games","Games")])
        body=f"""<p class="eyebrow">CFB MATCH LAB · OPPONENT-ADJUSTED DATA</p><h1>{season} College Football {label} Rankings</h1>
<p>{context}. {label} starts with the unit's season-to-date advanced performance, then applies a smooth 0.80×–1.20× multiplier based on the quality of the opposing units already faced. The adjusted results are converted back to a 1–100 FBS percentile.</p>
<p class="note">The opponent adjustment is unit-specific: offense is adjusted by defenses faced, while defense is adjusted by offenses faced. A 100 is the strongest end of the current FBS distribution.</p>
<div class="data-links"><a href="{BASE}/college-football-team-strength-rankings/"><b>Team Strength Rankings</b><br><span class="meta">Overall rating combines Offensive and Defensive Strength 50/50.</span></a><a href="{BASE}/college-football-strength-of-schedule-rankings/"><b>Strength of Schedule Rankings</b><br><span class="meta">See overall opponent difficulty already faced.</span></a></div>
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
