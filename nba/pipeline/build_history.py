#!/usr/bin/env python3
"""Build verified NBA regular-season game logs and team averages, 2015-16 onward.
Scheduled data collection entrypoint (archive build v1).
Outputs are staged in nba/teams/data; frontend consumes only these validated files.
Requires: pip install nba_api requests
"""
import json, time, argparse, datetime
from collections import defaultdict
from pathlib import Path
from nba_api.stats.endpoints import leaguegamefinder, leaguedashplayerstats

ROOT=Path(__file__).resolve().parents[1]/"teams"/"data"
SLUGS={"ATL":"atlanta-hawks","BOS":"boston-celtics","BKN":"brooklyn-nets","CHA":"charlotte-hornets","CHI":"chicago-bulls","CLE":"cleveland-cavaliers","DAL":"dallas-mavericks","DEN":"denver-nuggets","DET":"detroit-pistons","GSW":"golden-state-warriors","HOU":"houston-rockets","IND":"indiana-pacers","LAC":"la-clippers","LAL":"los-angeles-lakers","MEM":"memphis-grizzlies","MIA":"miami-heat","MIL":"milwaukee-bucks","MIN":"minnesota-timberwolves","NOP":"new-orleans-pelicans","NYK":"new-york-knicks","OKC":"oklahoma-city-thunder","ORL":"orlando-magic","PHI":"philadelphia-76ers","PHX":"phoenix-suns","POR":"portland-trail-blazers","SAC":"sacramento-kings","SAS":"san-antonio-spurs","TOR":"toronto-raptors","UTA":"utah-jazz","WAS":"washington-wizards"}
ALIASES={"GS":"GSW","SA":"SAS","NO":"NOP","NY":"NYK","UTAH":"UTA","WSH":"WAS"}
def clean(x):
    if x is None: return None
    try:
        import math
        if isinstance(x,float) and (math.isnan(x) or math.isinf(x)):return None
    except Exception:pass
    return x
def abbr(x):return ALIASES.get(x,x)
def safe_div(a,b,scale=1):return round(a/b*scale,2) if b else None
def collect(year):
    name=f"{year-1}-{str(year)[-2:]}"
    endpoint=leaguegamefinder.LeagueGameFinder(
       season_nullable=name,season_type_nullable="Regular Season",league_id_nullable="00",
       timeout=120)
    rows=endpoint.get_data_frames()[0].to_dict("records")
    rows=[{k:clean(v) for k,v in r.items()} for r in rows]
    valid=[r for r in rows if abbr(r.get("TEAM_ABBREVIATION")) in SLUGS and r.get("GAME_ID") and r.get("GAME_DATE")]
    bygame=defaultdict(list)
    for r in valid:bygame[str(r["GAME_ID"])].append(r)
    byteam=defaultdict(list)
    for gameid,group in bygame.items():
        if len(group)!=2 or group[0]["TEAM_ID"]==group[1]["TEAM_ID"]:continue
        for r,opp in ((group[0],group[1]),(group[1],group[0])):
            team=abbr(r["TEAM_ABBREVIATION"])
            if team not in SLUGS:continue
            matchup=r.get("MATCHUP","")
            home="vs." in matchup
            away="@" in matchup
            if not home and not away:continue
            points,against=r.get("PTS"),opp.get("PTS")
            if not isinstance(points,(int,float)) or not isinstance(against,(int,float)):continue
            byteam[team].append({
              "id":gameid,"date":str(r["GAME_DATE"])[:10],
              "opponent_name":opp.get("TEAM_NAME"),"opponent_abbr":abbr(opp["TEAM_ABBREVIATION"]),
              "location":"Home" if home else "Away",
              "result":"W" if points>against else "L",
              "score_for":int(points),"score_against":int(against),
              "_team":{k:r.get(k) for k in ("FGA","FGM","FG3A","FG3M","FTA","FTM","OREB","DREB","REB","AST","TOV","STL","BLK")},
              "_opp":{k:opp.get(k) for k in ("FGA","FGM","FG3A","FG3M","FTA","FTM","OREB","DREB","REB","AST","TOV","STL","BLK")}
            })
    result={}
    for team,slug in SLUGS.items():
        games=sorted(byteam[team],key=lambda g:g["date"])
        if not games:continue
        n=len(games); wins=sum(g["result"]=="W" for g in games)
        sums={side:{k:sum((g[side].get(k) or 0) for g in games) for k in ("FGA","FGM","FG3A","FG3M","FTA","FTM","OREB","DREB","REB","AST","TOV","STL","BLK")} for side in ("_team","_opp")}
        t,o=sums["_team"],sums["_opp"];pf=sum(g["score_for"] for g in games);pa=sum(g["score_against"] for g in games)
        possessions=t["FGA"]-t["OREB"]+t["TOV"]+0.44*t["FTA"]
        opp_poss=o["FGA"]-o["OREB"]+o["TOV"]+0.44*o["FTA"]
        avg_poss=(possessions+opp_poss)/2
        metrics={"ppg":round(pf/n,1),"points_allowed_per_game":round(pa/n,1),
          "fg_pct":safe_div(t["FGM"],t["FGA"],100),"three_pct":safe_div(t["FG3M"],t["FG3A"],100),
          "efg_pct":safe_div(t["FGM"]+0.5*t["FG3M"],t["FGA"],100),
          "ts_pct":safe_div(pf,2*(t["FGA"]+0.44*t["FTA"]),100),
          "ortg":safe_div(pf,avg_poss,100),"drtg":safe_div(pa,avg_poss,100),
          "net_rating":safe_div(pf-pa,avg_poss,100),"pace":round(avg_poss/n,1),
          "tov_pct":safe_div(t["TOV"],t["FGA"]+0.44*t["FTA"]+t["TOV"],100),
          "orb_pct":safe_div(t["OREB"],t["OREB"]+o["DREB"],100),
          "ft_rate":safe_div(t["FTA"],t["FGA"],100),
          "opp_efg_pct":safe_div(o["FGM"]+0.5*o["FG3M"],o["FGA"],100)}
        # These possession estimates are calculated from traditional box scores,
        # not official NBA tracking-based pace/advanced ratings.
        public=[{k:v for k,v in g.items() if not k.startswith("_")} for g in games]
        result[slug]={"key":str(year),"label":f"{year-1}–{str(year)[-2:]}",
          "coverage":"verified_games","updated_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "record":{"wins":wins,"losses":n-wins,"overall":f"{wins}-{n-wins}"},
          "metrics":metrics,"games":public,
          "metric_method":"estimated possessions from traditional box scores; regular season",
          "sources":[{"name":"NBA Stats via nba_api: LeagueGameFinder","url":"https://www.nba.com/stats/"}]}
    if len(result)!=30: raise ValueError(f"{name}: expected 30 teams, got {len(result)}")
    allids=defaultdict(list)
    for slug,row in result.items():
        ids=[g["id"] for g in row["games"]]
        if len(ids)!=len(set(ids)): raise ValueError(f"{name}: duplicate team games for {slug}")
        if len(ids)<55 or len(ids)>83: raise ValueError(f"{name}: implausible regular-season game count {len(ids)} for {slug}")
        for game_id in ids: allids[game_id].append(slug)
    if any(len(teams)!=2 for teams in allids.values()): raise ValueError(f"{name}: unpaired game records")
    print(f"{name}: {len(valid)} source rows, {len(result)} teams, {sum(len(v['games']) for v in result.values())} team-games")
    return result


def collect_players(year):
    """NBA Stats regular-season per-game roster averages, keyed by NBA team."""
    name=f"{year-1}-{str(year)[-2:]}"
    endpoint=leaguedashplayerstats.LeagueDashPlayerStats(
        season=name,season_type_all_star="Regular Season",per_mode_detailed="PerGame",
        measure_type_detailed_defense="Base",timeout=120)
    rows=endpoint.get_data_frames()[0].to_dict("records")
    grouped=defaultdict(list)
    for r in rows:
        ab=abbr(r.get("TEAM_ABBREVIATION"))
        if ab not in SLUGS or not r.get("GP"):continue
        def n(k):
            v=clean(r.get(k))
            return round(float(v),2) if isinstance(v,(int,float)) else None
        grouped[SLUGS[ab]].append({
          "name":r.get("PLAYER_NAME"),"player_id":r.get("PLAYER_ID"),"games":int(r["GP"]),
          "per_game":{"minutes":n("MIN"),"points":n("PTS"),"rebounds":n("REB"),
           "assists":n("AST"),"turnovers":n("TOV"),"steals":n("STL"),
           "blocks":n("BLK"),"fg_pct":n("FG_PCT"),"three_pct":n("FG3_PCT"),
           "ft_pct":n("FT_PCT")},
          "plus_minus":n("PLUS_MINUS"),
          "source":"NBA Stats: LeagueDashPlayerStats"})
    for players in grouped.values():
        players.sort(key=lambda p:(-(p["per_game"]["points"] or 0),p["name"] or ""))
    return grouped

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--from-season",type=int,default=2016);parser.add_argument("--through-season",type=int,default=2026);parser.add_argument("--players-season",type=int,default=2027);args=parser.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True)
    existing={}
    for slug in SLUGS.values():
        path=ROOT/(slug+".json")
        if path.exists():
            try: existing[slug]=json.loads(path.read_text())
            except Exception:existing[slug]={"seasons":[]}
        else:existing[slug]={"seasons":[]}
    for year in range(args.from_season,args.through_season+1):
        for attempt in range(3):
            try:
                data=collect(year);break
            except Exception as error:
                print(f"{year} attempt {attempt+1} failed: {error}")
                if attempt==2:raise
                time.sleep(10*(attempt+1))
        if len(data)!=30:raise ValueError(f"{year}: only {len(data)} of 30 teams; refusing incomplete season")
        for slug,row in data.items():
            prior=[s for s in existing[slug]["seasons"] if s["key"]!=str(year)]
            existing[slug]["seasons"]=sorted(prior+[row],key=lambda r:r["key"])
        time.sleep(1)
    # Player stats from the 2026-27 regular season are not fabricated from preseason games.
    # The requested current season is sampled separately, even before any regular games.
    for year in sorted(set([args.players_season,args.through_season])):
        try:
            players=collect_players(year)
            for slug,roster in players.items():
                match=next((v for v in existing[slug]["seasons"] if v["key"]==str(year)),None)
                if match is None:
                    match={"key":str(year),"label":f"{year-1}–{str(year)[-2:]}",
                           "coverage":"players_only","record":None,"metrics":{},"games":[],"sources":[]}
                    existing[slug]["seasons"].append(match)
                match["players"]=roster
                match["players_season_type"]="Regular Season"
                match["sources"].append({"name":"NBA Stats player averages","url":"https://www.nba.com/stats/players/traditional"})
            print(f"{year}: {sum(map(len,players.values()))} player-team rows")
        except Exception as error:
            # A season with no games can legitimately have no regular-season rows.
            print(f"Player averages for {year} unavailable: {error}")
    for slug,data in existing.items():
        data["seasons"].sort(key=lambda row:row["key"])
        if data["seasons"]:
            (ROOT/(slug+".json")).write_text(json.dumps(data,separators=(",",":"),ensure_ascii=False)+"\n")
    print("Validated JSON ready for all 30 teams")
if __name__=="__main__":main()
