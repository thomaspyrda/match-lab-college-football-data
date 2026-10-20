#!/usr/bin/env python3
"""Backfill 2026 MLB favorite/underdog sides from historical TeamRankings pages.

Uses official game ID, date, home/away records to construct archive links.
No inference from final scores. Checkpoint each batch; ambiguous doubleheaders
stay unresolved. Requests are modestly parallelized and honor robots.txt.
"""
import argparse, concurrent.futures, datetime, json, pathlib, random, re, time
import urllib.error, urllib.parse, urllib.request, urllib.robotparser
from collections import defaultdict
from collect_teamrankings_mlb import USER_AGENT, parse_page
from match_teamrankings_mlb import NAMES, match_season

ROOT=pathlib.Path(__file__).resolve().parents[1]
SLUG={v:k for k,v in NAMES.items()}
SLUG["cleveland-guardians"]="guardians"
SLUG["athletics"]="athletics"

def unique_finals(data):
    games=defaultdict(list)
    for team,entry in data["teams"].items():
        for game in entry.get("games",[]):
            games[str(game["game_id"])].append((team,game))
    pairs=[]
    counts=defaultdict(int)
    for game_id,rows in games.items():
        if len(rows)!=2:continue
        home=[team for team,g in rows if g.get("location")=="Home"]
        away=[team for team,g in rows if g.get("location")=="Away"]
        if len(home)!=1 or len(away)!=1:continue
        date=rows[0][1]["date"]
        counts[(date,home[0],away[0])]+=1
        pairs.append((game_id,date,home[0],away[0]))
    return pairs,counts

def fetch(item,robots,delay):
    game_id,date,home,away=item
    if home not in SLUG or away not in SLUG:return {"game_id":game_id,"status":"no_slug"}
    url=f"https://www.teamrankings.com/mlb/matchup/{SLUG[away]}-{SLUG[home]}-{date}/over-under-movement"
    if not robots.can_fetch(USER_AGENT,url):return {"game_id":game_id,"status":"robots"}
    time.sleep(delay)
    try:
        req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"text/html"})
        with urllib.request.urlopen(req,timeout=22) as r:
            if r.status!=200:return {"game_id":game_id,"status":str(r.status)}
            text=r.read(900000).decode("utf-8","replace")
        parsed=parse_page(text,url)
        if parsed["favorite_label"] and parsed["runline"]==1.5:
            return {"game_id":game_id,"url":url,"favorite_label":parsed["favorite_label"],"runline":1.5,"status":"found"}
        return {"game_id":game_id,"status":"no_favorite"}
    except urllib.error.HTTPError as e:
        return {"game_id":game_id,"status":"http_"+str(e.code)}
    except Exception as e:
        return {"game_id":game_id,"status":"error_"+type(e).__name__}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--season",type=int,default=2026)
    p.add_argument("--workers",type=int,default=4)
    p.add_argument("--delay",type=float,default=2)
    p.add_argument("--slice",type=int,default=0)
    p.add_argument("--slices",type=int,default=1)
    p.add_argument("--output",type=pathlib.Path,default=pathlib.Path("data/mlb/2026-teamrankings-favorites.json"))
    a=p.parse_args()
    if a.season!=2026:raise SystemExit("2026 only; protect other seasons")
    official=json.loads((ROOT/f"data/mlb/game-results/{a.season}.json").read_text())
    pairs,counts=unique_finals(official)
    pairs=sorted(pairs,key=lambda x:(x[1],x[0]))
    # Two scheduled games for the same clubs on one day need score-specific matching;
    # skip both instead of assigning the wrong favorite.
    eligible=[row for i,row in enumerate(pairs) if i%a.slices==a.slice and counts[(row[1],row[2],row[3])]==1]
    robots=urllib.robotparser.RobotFileParser()
    robots.set_url("https://www.teamrankings.com/robots.txt")
    robots.read()
    if not robots.can_fetch(USER_AGENT,"https://www.teamrankings.com/mlb/matchup/yankees-orioles-2026-08-20/over-under-movement"):
        raise SystemExit("Robots permission not confirmed")
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(a.workers,5))) as pool:
        futures=[pool.submit(fetch,row,robots,a.delay) for row in eligible]
        for i,f in enumerate(concurrent.futures.as_completed(futures),1):
            results.append(f.result())
            if i%50==0:print("processed",i,"of",len(eligible),flush=True)
    matches=[{k:v for k,v in r.items() if k in ("url","favorite_label","runline")} for r in results if r["status"]=="found"]
    statuses={}
    for r in results:statuses[r["status"]]=statuses.get(r["status"],0)+1
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps({"season":2026,"source":"TeamRankings historical game matchup favorite","matches":matches,"attempted":len(eligible),"status_counts":statuses},separators=(",",":"))+"\n")
    print(json.dumps({"eligible":len(eligible),"found":len(matches),"status_counts":statuses},indent=2))
if __name__=="__main__":main()
