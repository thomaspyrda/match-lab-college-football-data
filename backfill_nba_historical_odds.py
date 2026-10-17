#!/usr/bin/env python3
"""One-time, conservatively matched historical NBA odds backfill.
Game-level odds are source-recorded, NOT represented as verified closing lines.
"""
import argparse, csv, io, json, urllib.request
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parent
URL="https://raw.githubusercontent.com/aaryanshah607/nba-line-sheet/main/nba_odds_clean.csv"
DATA=ROOT/"nba/teams/data"
ALIASES={"Charlotte Bobcats":"Charlotte Hornets","New Orleans Hornets":"New Orleans Pelicans",
"New Jersey Nets":"Brooklyn Nets","LA Clippers":"Los Angeles Clippers",
"Los Angeles Clippers":"Los Angeles Clippers","Oklahoma City Thunder":"Oklahoma City Thunder"}
def norm(value):
    name=str(value or "").strip()
    return ALIASES.get(name,name).lower()

def row_for(game,team,rows):
    wanted=norm(game.get("opponent_name"))
    return [r for r in rows.get(game["date"],[]) if
            (norm(r["Home"])==team and norm(r["Away"])==wanted and game["location"]=="Home") or
            (norm(r["Away"])==team and norm(r["Home"])==wanted and game["location"]=="Away")]

def fill(game,row):
    is_home=game["location"]=="Home"
    own=int(game["score_for"]);opp=int(game["score_against"])
    if int(float(row["Points"]))!=own+opp:return None
    diff=float(row["Win_Margin"])
    if diff!=(own-opp if is_home else opp-own):return None
    try:
        ml_home=float(row["ML_Home"]);ml_away=float(row["ML_Away"])
        magnitude=abs(float(row["Spread"]))
        total=float(row["OU"])
        if ml_home==ml_away or not all(map(lambda x:abs(x)<1e6,[ml_home,ml_away,magnitude,total])):return None
    except (TypeError,ValueError):return None
    # Moneyline favorite selects the sign of the home-team handicap.
    home_line=-magnitude if ml_home<ml_away else magnitude
    team_line=home_line if is_home else -home_line
    ats_margin=own-opp+team_line
    ou_margin=own+opp-total
    return {"spread":team_line,"total":total,
            "ats_result":"W" if ats_margin>0 else "L" if ats_margin<0 else "P",
            "ou_result":"Over" if ou_margin>0 else "Under" if ou_margin<0 else "Push",
            "odds_source":"NBA line-sheet historical odds archive",
            "odds_source_url":"https://github.com/aaryanshah607/nba-line-sheet",
            "odds_line_type":"published_unspecified"}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args()
    with urllib.request.urlopen(URL,timeout=60) as response:
        raw=response.read().decode("utf-8")
    by_date={}
    for row in csv.DictReader(io.StringIO(raw)):
        by_date.setdefault(row["Date"],[]).append(row)
    report={}
    changed=0
    for path in sorted(DATA.glob("*-season-details.json")):
        doc=json.loads(path.read_text())
        slug=path.name.removesuffix("-season-details.json")
        # Slugs use historical team identity; season detail game records use full names.
        team=slug.replace("-"," ")
        # Normalize any franchise-name exceptions explicitly.
        special={"la-clippers":"Los Angeles Clippers","oklahoma-city-thunder":"Oklahoma City Thunder",
                 "portland-trail-blazers":"Portland Trail Blazers","golden-state-warriors":"Golden State Warriors",
                 "new-orleans-pelicans":"New Orleans Pelicans","new-york-knicks":"New York Knicks",
                 "san-antonio-spurs":"San Antonio Spurs","philadelphia-76ers":"Philadelphia 76ers"}
        team=norm(special.get(slug,team.title()))
        count=Counter()
        for year,season in doc.get("seasons",{}).items():
            if not 2016<=int(year)<=2026:continue
            for g in season.get("games",[]):
                count["games"]+=1
                matches=row_for(g,team,by_date)
                if len(matches)!=1:
                    count["unmatched"]+=1
                    continue
                fields=fill(g,matches[0])
                if fields is None:
                    count["ambiguous_or_score_mismatch"]+=1
                    continue
                g.update(fields);count["imported"]+=1
        report[slug]=dict(count)
        if count["imported"]:
            changed+=1
            if not args.dry_run:
                path.write_text(json.dumps(doc,separators=(",",":"),ensure_ascii=False)+"\n")
    totals=Counter()
    for item in report.values():totals.update(item)
    summary={"dry_run":args.dry_run,"teams_updated":changed,"totals":dict(totals),"teams":report}
    print(json.dumps(summary,indent=2))
    (ROOT/"nba/teams/data/backfill-audit.json").write_text(json.dumps(summary,indent=2)+"\n")
    if changed<25 or totals["imported"]<1000:
        raise SystemExit("Insufficient reliable matching; investigate before publishing")

if __name__=="__main__":
    main()
