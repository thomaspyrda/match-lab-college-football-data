#!/usr/bin/env python3
"""Safely match collected TeamRankings favorite labels to official MLB games.
Works on one date's collected archive; ambiguous pairings remain unresolved.
Does not alter scores. --write adds run-line sides only to unambiguous game IDs.
"""
import argparse, json, pathlib, re
ROOT=pathlib.Path(__file__).resolve().parents[1]
NAMES={"angels":"los-angeles-angels","astros":"houston-astros","athletics":"athletics",
"blue-jays":"toronto-blue-jays","braves":"atlanta-braves","brewers":"milwaukee-brewers",
"cardinals":"st-louis-cardinals","cubs":"chicago-cubs","diamondbacks":"arizona-diamondbacks",
"dodgers":"los-angeles-dodgers","giants":"san-francisco-giants","guardians":"cleveland-guardians",
"indians":"cleveland-guardians","mariners":"seattle-mariners","marlins":"miami-marlins",
"mets":"new-york-mets","nationals":"washington-nationals","orioles":"baltimore-orioles",
"padres":"san-diego-padres","phillies":"philadelphia-phillies","pirates":"pittsburgh-pirates",
"rangers":"texas-rangers","rays":"tampa-bay-rays","red-sox":"boston-red-sox",
"reds":"cincinnati-reds","rockies":"colorado-rockies","royals":"kansas-city-royals",
"tigers":"detroit-tigers","twins":"minnesota-twins","white-sox":"chicago-white-sox",
"yankees":"new-york-yankees"}
ALIASES={"arizona-diamondbacks":{"arizona"},"atlanta-braves":{"atlanta"},
"baltimore-orioles":{"baltimore"},"boston-red-sox":{"boston"},
"chicago-cubs":{"chicago"},"chicago-white-sox":{"chicago"},"cincinnati-reds":{"cincinnati"},
"cleveland-guardians":{"cleveland"},"colorado-rockies":{"colorado"},
"detroit-tigers":{"detroit"},"houston-astros":{"houston"},
"kansas-city-royals":{"kansas city"},"los-angeles-angels":{"los angeles"},
"los-angeles-dodgers":{"los angeles"},"miami-marlins":{"miami"},
"milwaukee-brewers":{"milwaukee"},"minnesota-twins":{"minnesota"},
"new-york-mets":{"new york"},"new-york-yankees":{"new york"},
"athletics":{"sacramento","oakland","athletics"},
"philadelphia-phillies":{"philadelphia"},"pittsburgh-pirates":{"pittsburgh"},
"san-diego-padres":{"san diego"},"san-francisco-giants":{"san francisco"},
"seattle-mariners":{"seattle"},"st-louis-cardinals":{"st. louis","st louis"},
"tampa-bay-rays":{"tampa bay"},"texas-rangers":{"texas"},
"toronto-blue-jays":{"toronto"},"washington-nationals":{"washington"}}
def parse_slug(url):
    m=re.search(r"/mlb/matchup/([a-z0-9-]+)-(20\d\d-\d\d-\d\d)(?:-([234]))?(?:/|$)",url)
    if not m:return None
    pair,date,number=m.groups()
    choices=[(a,b) for a in NAMES for b in NAMES if a!=b and pair==a+"-"+b]
    if len(choices)!=1:return None
    a,b=choices[0]
    return NAMES[a],NAMES[b],date,int(number or 1)
def match_season(official,source):
    byid={}
    for team,history in official["teams"].items():
        for game in history.get("games",[]):
            game_id=game.get("game_id")
            if game_id is not None:
                byid.setdefault(str(game_id),[]).append((team,game))
    indexed={}
    for game_id,rows in byid.items():
        if len(rows)!=2:continue
        teams={t for t,_ in rows}
        d={g.get("date") for _,g in rows}
        if len(d)!=1:continue
        indexed.setdefault((next(iter(d)),frozenset(teams)),[]).append((game_id,rows))
    stats={"parsed":0,"matched":0,"ambiguous":0,"missing":0,"favored_unknown":0}
    for item in source.get("matches",[]):
        parsed=parse_slug(item.get("url",""))
        if not parsed:stats["missing"]+=1;continue
        away,home,date,number=parsed
        stats["parsed"]+=1
        choices=indexed.get((date,frozenset((away,home))),[])
        # Two games on one date require explicit unique game sequence; do not guess based on URL -2.
        if len(choices)!=1:
            stats["ambiguous"]+=1;continue
        game_id,rows=choices[0]
        favorite_label=str(item.get("favorite_label") or "").strip().lower()
        favorites=[t for t in (away,home) if favorite_label in ALIASES.get(t,set())]
        if len(favorites)!=1:stats["favored_unknown"]+=1;continue
        favorite=favorites[0]
        if (away,home)!=(next((t for t,g in rows if g["location"]=="Away"),None),next((t for t,g in rows if g["location"]=="Home"),None)):
            stats["ambiguous"]+=1;continue
        for team,g in rows:
            if g.get("team_runline_side") in (-1.5,1.5):continue
            side=-1.5 if team==favorite else 1.5
            try:score,opponent=map(int,g["score"].split("-"))
            except (TypeError,ValueError):continue
            g["team_runline_side"]=side
            g["team_runline_result"]="W" if score+side>opponent else "L"
            g["runline_source"]="teamrankings"
            g["runline_source_url"]=item["url"]
        stats["matched"]+=1
    return stats
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",default="data/mlb/teamrankings-2018-day-pilot.json")
    p.add_argument("--season",type=int,default=2018)
    p.add_argument("--write",action="store_true")
    a=p.parse_args()
    file=ROOT/f"data/mlb/game-results/{a.season}.json"
    official=json.loads(file.read_text())
    source=json.loads((ROOT/a.source).read_text())
    stats=match_season(official,source)
    print(json.dumps(stats,indent=2))
    if a.write and stats["matched"]:
        file.write_text(json.dumps(official,separators=(",",":"))+"\n")
if __name__=="__main__":main()
