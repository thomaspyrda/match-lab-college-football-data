#!/usr/bin/env python3
"""Repair missing 2026-08-02 through 2026-08-13 MLB odds using ESPN archived game odds.
Only previously missing run-line sides are enriched; official results unchanged.
"""
import collections, concurrent.futures, datetime, json, pathlib, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
TEAMS={"ARI":"arizona-diamondbacks","ATL":"atlanta-braves","BAL":"baltimore-orioles","BOS":"boston-red-sox","CHC":"chicago-cubs","CHW":"chicago-white-sox","CWS":"chicago-white-sox","CIN":"cincinnati-reds","CLE":"cleveland-guardians","COL":"colorado-rockies","DET":"detroit-tigers","HOU":"houston-astros","KC":"kansas-city-royals","KCR":"kansas-city-royals","LAA":"los-angeles-angels","LAD":"los-angeles-dodgers","MIA":"miami-marlins","MIL":"milwaukee-brewers","MIN":"minnesota-twins","NYM":"new-york-mets","NYY":"new-york-yankees","OAK":"athletics","ATH":"athletics","PHI":"philadelphia-phillies","PIT":"pittsburgh-pirates","SD":"san-diego-padres","SDP":"san-diego-padres","SF":"san-francisco-giants","SFG":"san-francisco-giants","SEA":"seattle-mariners","STL":"st-louis-cardinals","TB":"tampa-bay-rays","TBR":"tampa-bay-rays","TEX":"texas-rangers","TOR":"toronto-blue-jays","WSH":"washington-nationals","WAS":"washington-nationals"}
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=24) as r:return json.load(r)
def side(odds):
    a=odds.get("awayTeamOdds") or {};h=odds.get("homeTeamOdds") or {}
    for aa,hh in ((a.get("open") or {},h.get("open") or {}),(a,h)):
        af=aa.get("favorite");hf=hh.get("favorite")
        if af is True and hf is not True:return "away"
        if hf is True and af is not True:return "home"
        def ml(x):
            val=x.get("moneyLine")
            if isinstance(val,dict):val=val.get("value")
            try:return float(val)
            except (TypeError,ValueError):return None
        av,hv=ml(aa),ml(hh)
        if av is not None and hv is not None and av!=hv:return "away" if av<hv else "home"
    return None
def get_day(d):
    try:
        day=fetch("https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates="+d.replace("-","")+"&limit=50")
        return d,day.get("events",[]),None
    except Exception as e:return d,[],repr(e)
def get_event(item):
    date,event=item
    comp=(event.get("competitions") or [{}])[0]
    loc={}
    for c in comp.get("competitors",[]):
        team=TEAMS.get((c.get("team") or {}).get("abbreviation","").upper())
        try:score=int(c.get("score"))
        except (ValueError,TypeError):score=None
        if team and score is not None:loc[c.get("homeAway")]=(team,score)
    if set(loc)!={"away","home"}:return None,"team_or_score"
    eid=str(event["id"])
    url=f"https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/events/{eid}/competitions/{eid}/odds"
    try:odds=fetch(url).get("items") or []
    except Exception as e:return None,"odds_http_error"
    favored={side(x) for x in odds}-{None}
    totals={float(x["overUnder"]) for x in odds if isinstance(x.get("overUnder"),(int,float)) and x["overUnder"]>0}
    return {"date":date,"home":loc["home"],"away":loc["away"],"favored":next(iter(favored)) if len(favored)==1 else None,"total":next(iter(totals)) if len(totals)==1 else None,"url":url},None
def main():
    path=ROOT/"data/mlb/game-results/2026.json"
    data=json.loads(path.read_text())
    grouped=collections.defaultdict(list)
    for team,record in data["teams"].items():
        for g in record["games"]:grouped[g["game_id"]].append((team,g))
    # Unique ESPN match key includes both final scores to distinguish doubleheaders.
    lookup=collections.defaultdict(list)
    for gid,records in grouped.items():
        if len(records)!=2:continue
        home=next(((t,g) for t,g in records if g.get("location")=="Home"),None)
        away=next(((t,g) for t,g in records if g.get("location")=="Away"),None)
        if home and away and isinstance(home[1].get("runs_for"),int) and isinstance(away[1].get("runs_for"),int):
            lookup[(home[1]["date"],home[0],away[0],home[1]["runs_for"],away[1]["runs_for"])].append(records)
    dates=[(datetime.date(2026,8,2)+datetime.timedelta(days=i)).isoformat() for i in range(12)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:days=list(ex.map(get_day,dates))
    events=[(d,e) for d,items,err in days for e in items]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:found=list(ex.map(get_event,events))
    stats=collections.Counter()
    stats["scoreboard_errors"]=sum(err is not None for d,items,err in days)
    stats["events"]=len(events)
    for obj,err in found:
        if err:stats[err]+=1;continue
        h,hs=obj["home"];a,ascore=obj["away"]
        keys=lookup.get((obj["date"],h,a,hs,ascore),[])
        if len(keys)!=1:stats["official_match_missing_or_duplicate"]+=1;continue
        rows=keys[0]
        if obj["total"] is not None:
            for team,g in rows:
                if g.get("market_ou_total") is None:
                    total=obj["total"]
                    g["market_ou_total"]=total
                    scored=g["runs_for"]+g["runs_against"]
                    g["market_ou_result"]="O" if scored>total else "U" if scored<total else "P"
                    g["market_ou_source"]="espn_historical_aug_2026"
            stats["totals_recovered"]+=1
        if all(g.get("team_runline_side") in (-1.5,1.5) for t,g in rows):
            stats["already_populated"]+=1
            continue
        if any(g.get("team_runline_side") in (-1.5,1.5) for t,g in rows):
            stats["partial_pair"]+=1
            continue
        if obj["favored"] is None:
            stats["missing_or_disputed_favorite"]+=1
            continue
        favorite=h if obj["favored"]=="home" else a
        for team,g in rows:
            line=-1.5 if team==favorite else 1.5
            g["team_runline_side"]=line
            g["team_runline_result"]="W" if g["runs_for"]+line>g["runs_against"] else "L"
            g["runline_source"]="espn_historical_aug_2026"
            g["runline_source_url"]=obj["url"]
        stats["added"]+=1
    path.write_text(json.dumps(data,separators=(",",":"))+"\n")
    print(json.dumps(stats,indent=2),flush=True)
    assert stats["totals_recovered"]>30,"Insufficient August O/U coverage"
if __name__=="__main__":main()
