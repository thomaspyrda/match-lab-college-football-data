#!/usr/bin/env python3
"""Build checked 2015-16 through 2019-20 NBA coaching history from a published CSV.
Source: https://github.com/spoonertaylor/NBA_Coaches (basketball-reference-derived).
This is a PARTIAL archive; do not label 2020-21 onward complete.
"""
import csv,io,json,urllib.request
from collections import defaultdict
from pathlib import Path
from nba_api.stats.endpoints import commonteamroster
from nba_api.stats.static import teams as nba_teams
import time
SOURCE="https://raw.githubusercontent.com/spoonertaylor/NBA_Coaches/master/coaches_long.csv"
OUT=Path(__file__).resolve().parents[1]/"teams"/"data"/"coaching-history.json"
ABBR={"PHO":"PHX","NYK":"NYK","BRK":"BKN","NJN":"BKN","NOH":"NOP","NOK":"NOP","SEA":"OKC","WSB":"WAS","CHH":"CHA","CHO":"CHA"}
NAMES={"ATL":"atlanta-hawks","BOS":"boston-celtics","BKN":"brooklyn-nets","CHA":"charlotte-hornets","CHI":"chicago-bulls","CLE":"cleveland-cavaliers","DAL":"dallas-mavericks","DEN":"denver-nuggets","DET":"detroit-pistons","GSW":"golden-state-warriors","HOU":"houston-rockets","IND":"indiana-pacers","LAC":"la-clippers","LAL":"los-angeles-lakers","MEM":"memphis-grizzlies","MIA":"miami-heat","MIL":"milwaukee-bucks","MIN":"minnesota-timberwolves","NOP":"new-orleans-pelicans","NYK":"new-york-knicks","OKC":"oklahoma-city-thunder","ORL":"orlando-magic","PHI":"philadelphia-76ers","PHX":"phoenix-suns","POR":"portland-trail-blazers","SAC":"sacramento-kings","SAS":"san-antonio-spurs","TOR":"toronto-raptors","UTA":"utah-jazz","WAS":"washington-wizards"}
def main():
    req=urllib.request.Request(SOURCE,headers={"User-Agent":"BetWiseResearch/1.0"})
    with urllib.request.urlopen(req,timeout=45) as resp: content=resp.read().decode("utf-8-sig")
    rows=list(csv.DictReader(io.StringIO(content)))
    result=defaultdict(dict)
    for r in rows:
        year=int(r["season"])
        if year<2016 or year>2020:continue
        abbr=ABBR.get(r["team_abbrv"],r["team_abbrv"])
        if abbr not in NAMES:continue
        slug=NAMES[abbr]
        result[slug].setdefault(str(year),[]).append({
            "name":r["coach_name"],"games":int(r["games_coached"]),
            "wins":int(r["games_W"]),"losses":int(r["games_L"]),
            "order":int(r["team_coach_number"])})
    for year in range(2016,2021):
        missing=[slug for slug in NAMES.values() if str(year) not in result[slug]]
        if missing:raise ValueError(f"Missing coaches for {year}: {missing}")
    for seasons in result.values():
        for year,coaches in seasons.items():
            coaches.sort(key=lambda c:c["order"])
            total=sum(c["games"] for c in coaches)
            if not 55<=total<=83:raise ValueError(f"Invalid games {year}: {total}")
    # For later seasons use official NBA team coaching rosters, but do not
    # silently infer that a single roster contains midseason departures.
    ids={t["abbreviation"]:t["id"] for t in nba_teams.get_teams()}
    for year in range(2021,2028):
        season=f"{year-1}-{str(year)[-2:]}"
        for ab,slug in NAMES.items():
            try:
                ep=commonteamroster.CommonTeamRoster(team_id=ids[ab],season=season,timeout=30)
                rows=ep.coaches.get_data_frame().to_dict("records")
                coaches=[r for r in rows if not bool(r.get("IS_ASSISTANT")) and
                         (str(r.get("COACH_TYPE","")).strip().lower() in ("head coach","headcoach","hc") or
                          str(r.get("COACH_TYPE","")).strip().lower().startswith("head"))]
                if coaches:
                    result[slug][str(year)]=[{"name":r.get("COACH_NAME") or
                       (str(r.get("FIRST_NAME",""))+" "+str(r.get("LAST_NAME",""))).strip(),
                       "games":None,"wins":None,"losses":None,
                       "order":i+1,"status":"staff_roster_not_game_validated"}
                       for i,r in enumerate(coaches)]
                time.sleep(0.2)
            except Exception as exc:
                print(f"Coach roster unavailable: {slug} {season}: {exc}")
    # Keep NBA.com as the canonical verification destination for every entry.
    # Staff roster snapshots are NOT deemed fully verified season histories.
    for slug,seasons in result.items():
        for year,coaches in seasons.items():
            for coach in coaches:
                coach["verification_source"]="https://www.nba.com/"
                coach["verification_status"]=("historical_source_checked" if int(year)<=2020 else "requires_nba_com_historical_crosscheck")
    out={"coverage":{"start":2016,"end":2027,"complete_through":2020,"note":"2015-16 to 2019-20 game-based records; 2020-21 onward staff roster snapshots only, may omit interims and departures"},
         "source":SOURCE,"teams":dict(result)}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(",",":"))+"\n")
    print(f"Produced {sum(len(x) for x in result.values())} team-season records across {len(result)} teams; 2021+ not certified complete")
if __name__=="__main__":main()
