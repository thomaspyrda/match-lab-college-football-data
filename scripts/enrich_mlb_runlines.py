#!/usr/bin/env python3
"""Enrich official MLB game results using a separately obtained SBR historical JSON archive.

Usage: python scripts/enrich_mlb_runlines.py --odds /path/to/mlb_odds.json --season 2024
Source format: https://github.com/ArnavSaraogi/mlb-odds-scraper
Does not retrieve copyrighted/provider data or change official score/results.
"""
import argparse
import collections
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SLUG_TO_CODE = {
"arizona-diamondbacks":"ARI","atlanta-braves":"ATL","baltimore-orioles":"BAL",
"boston-red-sox":"BOS","chicago-cubs":"CHC","chicago-white-sox":"CWS",
"cincinnati-reds":"CIN","cleveland-guardians":"CLE","colorado-rockies":"COL",
"detroit-tigers":"DET","houston-astros":"HOU","kansas-city-royals":"KC",
"los-angeles-angels":"LAA","los-angeles-dodgers":"LAD","miami-marlins":"MIA",
"milwaukee-brewers":"MIL","minnesota-twins":"MIN","new-york-mets":"NYM",
"new-york-yankees":"NYY","athletics":"ATH","oakland-athletics":"OAK",
"philadelphia-phillies":"PHI","pittsburgh-pirates":"PIT","san-diego-padres":"SD",
"san-francisco-giants":"SF","seattle-mariners":"SEA","st-louis-cardinals":"STL",
"tampa-bay-rays":"TB","texas-rangers":"TEX","toronto-blue-jays":"TOR",
"washington-nationals":"WSH"}
ALIASES = {"OAK":"ATH","ATH":"ATH","AZ":"ARI","CHW":"CWS","CIN":"CIN","WSH":"WSH","WAS":"WSH","CHC":"CHC","SF":"SF","SD":"SD","KC":"KC","TB":"TB","LAD":"LAD","LAA":"LAA"}
BOOK_PRIORITY = ("fanduel","draftkings","betmgm","caesars","bet365","betrivers")

def code(v):
    if isinstance(v, dict):
        v=v.get("shortName") or v.get("abbreviation") or v.get("fullName")
    if not v: return None
    raw=str(v).strip()
    upper=raw.upper()
    if upper in ALIASES:return ALIASES[upper]
    if upper in SLUG_TO_CODE.values():return upper
    return SLUG_TO_CODE.get(raw.lower())

def key(date,home,away,home_score,away_score):
    return (date,code(home),code(away),int(home_score),int(away_score))

def select_side(game):
    """Use actual posted standard run-line side, then sportsbook closing moneyline fallback."""
    odds=game.get("odds") or {}
    for book in BOOK_PRIORITY:
        for entry in odds.get("pointspread",[]):
            if str(entry.get("sportsbook","")).lower()!=book: continue
            line=entry.get("currentLine") or entry.get("openingLine") or {}
            h,a=line.get("homeSpread"),line.get("awaySpread")
            try: h,a=float(h),float(a)
            except (ValueError,TypeError):continue
            if (h,a) in ((-1.5,1.5),(1.5,-1.5)):
                return h,book,"pointspread"
    for book in BOOK_PRIORITY:
        for entry in odds.get("moneyline",[]):
            if str(entry.get("sportsbook","")).lower()!=book:continue
            line=entry.get("currentLine") or entry.get("openingLine") or {}
            try: h,a=int(line["homeOdds"]),int(line["awayOdds"])
            except (ValueError,TypeError,KeyError):continue
            if h==a:continue
            return (-1.5 if h<a else 1.5),book,"moneyline_inferred"
    return None,None,None

def candidates(archive,season):
    matched=collections.defaultdict(list)
    for day,items in archive.items():
        if not str(day).startswith(str(season)+"-") or not isinstance(items,list):continue
        for item in items:
            v=item.get("gameView") or {}
            if v.get("gameType") not in (None,"R"):continue
            try:
                identity=key(day,v.get("homeTeam"),v.get("awayTeam"),v.get("homeTeamScore"),v.get("awayTeamScore"))
                if not all(identity[:3]):continue
            except (TypeError,ValueError):continue
            side,book,method=select_side(item)
            if side is not None: matched[identity].append((side,book,method))
    return matched

def enrich(official,archive,season):
    choices=candidates(archive,season)
    indexed=collections.defaultdict(list)
    for slug,entry in official["teams"].items():
        team=code(slug)
        for game in entry.get("games",[]):
            for old_field in ("team_runline_side","team_runline_result","runline_source","runline_book","runline_method"):
                game.pop(old_field,None)
            if game.get("result") not in ("W","L"):continue
            home=team if game.get("location")=="Home" else code(game.get("opponent"))
            away=team if game.get("location")=="Away" else code(game.get("opponent"))
            try:
                team_score,opponent_score=map(int,str(game.get("score","")).split("-"))
            except (ValueError,TypeError):continue
            home_score,away_score=(team_score,opponent_score) if game.get("location")=="Home" else (opponent_score,team_score)
            identity=key(game.get("date"),home,away,home_score,away_score)
            indexed[identity].append((game,team,game.get("location")))
    stats=collections.Counter()
    for identity,rows in indexed.items():
        # One identity is one real game represented on two separate team pages.
        if len(rows)!=2 or set(x[2] for x in rows)!={"Home","Away"} or len({x[1] for x in rows})!=2:
            stats["ambiguous_official_games"]+=1
            continue
        odds=choices.get(identity,[])
        unique=set(x[0] for x in odds)
        if len(unique)!=1:
            stats["missing_or_disputed_odds"]+=1
            continue
        home_side=next(iter(unique))
        book=next(x[1] for x in odds if x[0]==home_side)
        method=next(x[2] for x in odds if x[0]==home_side)
        for game,_,location in rows:
            side=home_side if location=="Home" else -home_side
            team_score,opponent_score=map(int,game["score"].split("-"))
            cover=team_score+side>opponent_score
            game["team_runline_side"]=side
            game["team_runline_result"]="W" if cover else "L"
            game["runline_source"]="sportsbookreview"
            game["runline_book"]=book
            game["runline_method"]=method
        stats["enriched_games"]+=1
    for entry in official["teams"].values():
        games=[g for g in entry.get("games",[]) if g.get("team_runline_result") in ("W","L")]
        if not isinstance(entry.get("record"),dict):entry["record"]={}
        entry["record"]["verified_runline_wins"]=sum(g["team_runline_result"]=="W" for g in games)
        entry["record"]["verified_runline_losses"]=sum(g["team_runline_result"]=="L" for g in games)
        entry["record"]["verified_runline_games"]=len(games)
    stats["enriched_games"]+=0
    stats["missing_or_disputed_odds"]+=0
    stats["ambiguous_official_games"]+=0
    stats["official_game_identifiers"]=len(indexed)
    stats["source_identities"]=len(choices)
    stats["matched_pct"]=round(100*stats["enriched_games"]/len(indexed),2) if indexed else 0
    return dict(stats)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--odds",required=True)
    parser.add_argument("--season",type=int,required=True)
    parser.add_argument("--write",action="store_true",help="Update published season JSON; otherwise validation-only")
    args=parser.parse_args()
    target=ROOT/"data"/"mlb"/"game-results"/f"{args.season}.json"
    archive=json.loads(pathlib.Path(args.odds).read_text())
    official=json.loads(target.read_text())
    result=enrich(official,archive,args.season)
    print(json.dumps(result,indent=2))
    if args.write:
        if not result.get("enriched_games"):raise SystemExit("No verified matches; refusing to overwrite")
        tmp=target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(official,separators=(",",":"))+"\n")
        tmp.replace(target)
        print("Updated",target)

if __name__=="__main__":main()
