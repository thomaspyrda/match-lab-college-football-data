#!/usr/bin/env python3
"""Collect dated TeamRankings NBA team statistical snapshots for 2015-16 onward.
Source values are preserved exactly; provenance and season scope are explicit.
"""
import argparse, json, re, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests

OUT = Path(__file__).resolve().parents[1] / "teams" / "data"
STATS = {
    "points-per-game": "ppg",
    "opponent-points-per-game": "points_allowed_per_game",
    "offensive-efficiency": "ortg",
    "defensive-efficiency": "drtg",
    "effective-field-goal-pct": "efg_pct",
    "true-shooting-percentage": "ts_pct",
    "opponent-effective-field-goal-pct": "opp_efg_pct",
    "turnovers-per-possession": "tov_pct",
    "offensive-rebounding-pct": "orb_pct",
    "possessions-per-game": "pace",
}
TEAMS = {
    "Atlanta":"atlanta-hawks","Boston":"boston-celtics","Brooklyn":"brooklyn-nets",
    "Charlotte":"charlotte-hornets","Chicago":"chicago-bulls","Cleveland":"cleveland-cavaliers",
    "Dallas":"dallas-mavericks","Denver":"denver-nuggets","Detroit":"detroit-pistons",
    "Golden State":"golden-state-warriors","Houston":"houston-rockets",
    "Indiana":"indiana-pacers","LA Clippers":"la-clippers","LA Lakers":"los-angeles-lakers",
    "Memphis":"memphis-grizzlies","Miami":"miami-heat","Milwaukee":"milwaukee-bucks",
    "Minnesota":"minnesota-timberwolves","New Orleans":"new-orleans-pelicans",
    "New York":"new-york-knicks","Okla City":"oklahoma-city-thunder",
    "Oklahoma City":"oklahoma-city-thunder","Orlando":"orlando-magic",
    "Philadelphia":"philadelphia-76ers","Phoenix":"phoenix-suns",
    "Portland":"portland-trail-blazers","Sacramento":"sacramento-kings",
    "San Antonio":"san-antonio-spurs","Toronto":"toronto-raptors",
    "Utah":"utah-jazz","Washington":"washington-wizards",
}
def snapshot(year):
    if year == 2020: return "2020-10-20"
    if year == 2021: return "2021-07-25"
    return f"{year}-07-10"

def fetch(stat, year, session):
    url=f"https://www.teamrankings.com/nba/stat/{stat}?date={snapshot(year)}"
    response=session.get(url,timeout=45)
    response.raise_for_status()
    tables=pd.read_html(response.text)
    for df in tables:
        columns=[str(c) for c in df.columns]
        if "Team" not in columns or str(year-1) not in columns: continue
        entries={}
        for _, row in df.iterrows():
            team=TEAMS.get(str(row["Team"]).strip())
            if not team: continue
            raw=str(row[str(year-1)]).replace("%","").replace(",","")
            try: value=float(raw)
            except ValueError: continue
            if team in entries: raise ValueError(f"Duplicate {team}: {url}")
            entries[team]=value
        if len(entries)==30: return url,entries
    raise ValueError(f"Unable to parse 30 teams and {year-1} column at {url}")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--first",type=int,default=2016)
    parser.add_argument("--last",type=int,default=2026)
    args=parser.parse_args()
    if args.first<2016 or args.last>2026 or args.first>args.last: raise ValueError("Invalid seasons")
    session=requests.Session()
    session.headers.update({"User-Agent":"Mozilla/5.0","Accept":"text/html"})
    output={}
    coverage={}
    for year in range(args.first,args.last+1):
        rows={slug:{} for slug in set(TEAMS.values())}
        sources={}
        for url_slug,key in STATS.items():
            try:
                url,values=fetch(url_slug,year,session)
                for slug,value in values.items(): rows[slug][key]=value
                sources[key]=url
                print(f"{year} {key}: {len(values)} teams",flush=True)
            except Exception as ex:
                coverage[f"{year}:{key}"]={"error":str(ex)}
                print(f"Unavailable {year} {key}: {ex}",flush=True)
            time.sleep(1)
        # Do not publish a season unless all configured metrics cover all teams.
        if any(len(vals)!=len(STATS) for vals in rows.values()): continue
        for slug,metrics in rows.items():
            output.setdefault(slug,{})[str(year)]={
                "metrics":metrics, "as_of":snapshot(year),
                "source":"TeamRankings","source_urls":sources,
                "scope":"dated historical snapshot; may include postseason",
                "regular_season_only":False
            }
        coverage[str(year)]={"teams":30,"metrics":len(STATS)}
    OUT.mkdir(parents=True,exist_ok=True)
    for slug, seasons in output.items():
        (OUT/f"{slug}-teamrankings.json").write_text(
            json.dumps({"team":slug,"seasons":seasons},indent=2)+"\n")
    (OUT/"teamrankings-coverage.json").write_text(json.dumps(coverage,indent=2)+"\n")
    if not output: raise RuntimeError("No complete seasons returned by TeamRankings")
    print(f"Published {len(output)} NBA team archives",flush=True)

if __name__=="__main__": main()
