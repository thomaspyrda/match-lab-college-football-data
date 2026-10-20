#!/usr/bin/env python3
"""Enrich official 2026 MLB finals with ESPN archived odds and record-based conflict estimates."""
import collections, concurrent.futures, json, pathlib, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
TEAMS={"ARI":"arizona-diamondbacks","ATL":"atlanta-braves","BAL":"baltimore-orioles","BOS":"boston-red-sox","CHC":"chicago-cubs","CHW":"chicago-white-sox","CWS":"chicago-white-sox","CIN":"cincinnati-reds","CLE":"cleveland-guardians","COL":"colorado-rockies","DET":"detroit-tigers","HOU":"houston-astros","KC":"kansas-city-royals","LAA":"los-angeles-angels","LAD":"los-angeles-dodgers","MIA":"miami-marlins","MIL":"milwaukee-brewers","MIN":"minnesota-twins","NYM":"new-york-mets","NYY":"new-york-yankees","OAK":"athletics","ATH":"athletics","PHI":"philadelphia-phillies","PIT":"pittsburgh-pirates","SD":"san-diego-padres","SF":"san-francisco-giants","SEA":"seattle-mariners","STL":"st-louis-cardinals","TB":"tampa-bay-rays","TEX":"texas-rangers","TOR":"toronto-blue-jays","WSH":"washington-nationals"}
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}),timeout=25) as r:return json.load(r)
def favorite(item):
    a=item.get("awayTeamOdds") or {}; h=item.get("homeTeamOdds") or {}
    for aa,hh in ((a.get("open") or {},h.get("open") or {}),(a,h)):
        if aa.get("favorite") is True and hh.get("favorite") is not True:return "away"
        if hh.get("favorite") is True and aa.get("favorite") is not True:return "home"
        am=aa.get("moneyLine");hm=hh.get("moneyLine")
        if isinstance(am,dict):am=am.get("value")
        if isinstance(hm,dict):hm=hm.get("value")
        try:
            if float(am)!=float(hm):return "away" if float(am)<float(hm) else "home"
        except (TypeError,ValueError):pass
    return None
def odds_event(event):
    comp=(event.get("competitions") or [{}])[0]
    teams={}
    for c in comp.get("competitors",[]):
        team=TEAMS.get((c.get("team") or {}).get("abbreviation","").upper())
        if team:teams[c.get("homeAway")]=(team,int(c.get("score") or 0))
    if set(teams)!={"home","away"}:return None
    eid=str(event["id"])
    url=f"https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/events/{eid}/competitions/{eid}/odds"
    try:items=fetch(url).get("items") or []
    except Exception:return None
    sides={favorite(i) for i in items}-{None}
    return {"teams":teams,"url":url,"sides":sides}
def main():
    path=ROOT/"data/mlb/game-results/2026.json";data=json.loads(path.read_text())
    byid=collections.defaultdict(list)
    for t,entry in data["teams"].items():
        for g in entry["games"]:byid[str(g["game_id"])].append((t,g))
    official={}
    for gid,rows in byid.items():
        if len(rows)!=2:continue
        home=next(((t,g) for t,g in rows if g.get("location")=="Home"),None)
        away=next(((t,g) for t,g in rows if g.get("location")=="Away"),None)
        if home and away:
            official[(home[1]["date"],home[0],away[0],home[1]["runs_for"],away[1]["runs_for"])]=rows
    # Standings as-of the night before each scheduled game, including doubleheaders.
    pregame=collections.defaultdict(dict)
    for team,history in data["teams"].items():
        w=l=0
        for g in sorted(history["games"],key=lambda x:(x["date"],x["game_id"])):
            pregame[team][str(g["game_id"])]=(w,l)
            if g["result"]=="W":w+=1
            elif g["result"]=="L":l+=1
    days=sorted({key[0] for key in official})
    def get_day(day):
        try:return day,fetch("https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates="+day.replace("-","")+"&limit=50").get("events",[])
        except Exception:return day,[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:daily=list(pool.map(get_day,days))
    events=[(day,event) for day,events in daily for event in events]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:odds=list(pool.map(odds_event,(event for _,event in events)))
    counts=collections.Counter()
    for (day,event),o in zip(events,odds):
        if not o:counts["no_odds"]+=1;continue
        home,away=o["teams"]["home"],o["teams"]["away"]
        key=(day,home[0],away[0],home[1],away[1])
        rows=official.get(key)
        if not rows:counts["no_official_match"]+=1;continue
        if any(g.get("team_runline_side") in (-1.5,1.5) for _,g in rows):
            counts["already_published"]+=1;continue
        if len(o["sides"])==1:
            favor=home[0] if "home" in o["sides"] else away[0]
            source="espn_historical_odds"
        elif len(o["sides"])>1:
            # Only on actual ESPN source conflict: use better entering-game win percentage.
            gameid=str(rows[0][1]["game_id"])
            aw,al=pregame[away[0]][gameid];hw,hl=pregame[home[0]][gameid]
            ap=aw/(aw+al) if aw+al else .5;hp=hw/(hw+hl) if hw+hl else .5
            if ap==hp:counts["tied_records"]+=1;continue
            favor=away[0] if ap>hp else home[0]
            source="estimated_pregame_record_conflicting_odds"
        else:counts["no_favorite"]+=1;continue
        for team,g in rows:
            side=-1.5 if team==favor else 1.5
            g["team_runline_side"]=side;g["team_runline_result"]="W" if g["runs_for"]+side>g["runs_against"] else "L"
            g["runline_source"]=source;g["runline_source_url"]=o["url"]
            if source.startswith("estimated"):g["runline_estimated"]=True
        counts[source]+=1
    path.write_text(json.dumps(data,separators=(",",":"))+"\n")
    print(json.dumps(counts,indent=2))
if __name__=="__main__":main()
