"""Reconstruct CBB game-level shooting, rebounding and assist profiles from CBBD.
Requires CBBD_API_KEY in Actions secrets. Outputs a compact, per-game snapshot index.
No season-ending averages, rankings, or missing-value zeros are introduced.
"""
import argparse,json,os,math
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from backfill_cbb_cbdd_history import window

ROOT=Path(__file__).resolve().parent
def v(x):
 try:
  if x is None or x=="":return None
  n=float(x)
  return n if math.isfinite(n) else None
 except (ValueError,TypeError):return None
def nested(d,*keys):
 for k in keys:
  if not isinstance(d,dict):return None
  d=d.get(k)
 return d
def measure(row,section,name,field="total"):
 section_data=row.get(section) or {}
 item=section_data.get(name) or {}
 if isinstance(item,(int,float)):return v(item)
 if isinstance(item,dict):
  for fieldname in (field,"total","value","count"):
   if fieldname in item:
    found=v(item[fieldname])
    if found is not None:return found
 return None
def derive(r):
 own=r.get("teamStats") or {};opp=r.get("opponentStats") or {}
 # Require numerical make/attempt pairs: never use missing as zero.
 def made_attempt(stats,kind):
  s=stats.get(kind) or {}
  m=v(s.get("made") or s.get("makes"));a=v(s.get("attempted") or s.get("attempts"))
  return (m,a) if m is not None and a is not None and a>0 and 0<=m<=a else (None,None)
 fg, fga=made_attempt(own,"fieldGoals");th,tha=made_attempt(own,"threePointFieldGoals")
 ofg,ofga=made_attempt(opp,"fieldGoals");oth,otha=made_attempt(opp,"threePointFieldGoals")
 ft,fta=made_attempt(own,"freeThrows")
 values={"oreb_pg":measure(r,"teamStats","rebounds","offensive"),"dreb_pg":measure(r,"teamStats","rebounds","defensive"),
  "assists_pg":measure(r,"teamStats","assists"),"opp_assists_pg":measure(r,"opponentStats","assists"),
  "pace":v(r.get("pace")),"turnovers":measure(r,"teamStats","turnovers"),
  "opponent_turnovers":measure(r,"opponentStats","turnovers")}
 if None not in (th,tha):values["three_pct"]=100*th/tha
 if None not in (oth,otha):values["opp_three_pct"]=100*oth/otha
 if None not in (fg,fga,th):values["efg_pct"]=100*(fg+0.5*th)/fga
 if None not in (ofg,ofga,oth):values["opp_efg_pct"]=100*(ofg+0.5*oth)/ofga
 if None not in (ft,fta):values["ft_pct"]=100*ft/fta
 if values["turnovers"] is not None and values["opponent_turnovers"] is not None:
  values["turnover_margin"]=values["opponent_turnovers"]-values["turnovers"]
 return {k:round(n,5) for k,n in values.items() if n is not None}
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--season",type=int,required=True)
 args=parser.parse_args()
 if not os.getenv("CBBD_API_KEY"):raise SystemExit("CBBD_API_KEY Actions secret required")
 year=args.season
 first=datetime(year-1,10,1,tzinfo=timezone.utc);last=datetime(year,5,31,23,59,59,tzinfo=timezone.utc)
 byteam=defaultdict(list)
 # Exact crosswalk: CBBD game sourceId is ESPN game ID. Resolve each ESPN
 # team's ID from its archived schedule; never fuzzy-match school names.
 registry=json.loads((ROOT/"data/sports/team-registry.json").read_text())["teams"]
 espn_home={}
 for school in registry:
  if school.get("sport")!="cbb":continue
  path=ROOT/f"data/cbb/teams/{school['slug']}.json"
  if not path.exists():continue
  archive=json.loads(path.read_text()).get("seasons",{}).get(str(year),{})
  for phase in archive.get("phases",{}).values():
   for game in phase.get("games",[]):
    if game.get("location") in ("Home","Away"):
     espn_home[(str(game.get("id")),game["location"])]=str(school["espn_id"])
 cur=first
 while cur<=last:
  stop=min(last,cur+timedelta(days=30))
  games=window("/games",year,cur,stop)
  dates={str(g.get("id") or g.get("gameId")):g.get("startDate") or g.get("startTime") for g in games}
  crosswalk={}
  for g in games:
   cbid=str(g.get("id") or g.get("gameId") or "")
   source=str(g.get("sourceId") or "")
   if not cbid or not source:continue
   for location,key in (("Home","homeTeamId"),("Away","awayTeamId")):
    eid=espn_home.get((source,location))
    if eid and g.get(key) is not None:
     crosswalk[(cbid,str(g[key]))]=(source,eid)
  for row in window("/games/teams",year,cur,stop):
   gid=str(row.get("gameId") or "");tid=str(row.get("teamId") or "")
   started=row.get("startDate") or dates.get(gid)
   mapped=crosswalk.get((gid,tid))
   if not gid or not tid or not started or not mapped:continue
   espn_game,espn_team=mapped
   values=derive(row)
   byteam[espn_team].append({"game_id":espn_game,"date":started,"stats":values})
  cur=stop+timedelta(microseconds=1)
 snapshots={}
 for tid,rows in byteam.items():
  rows.sort(key=lambda g:(g["date"],g["game_id"]))
  for game in rows:
   # Same-date games excluded, avoiding leakage when kickoff precision is unavailable.
   previous=[r for r in rows if r["date"][:10]<game["date"][:10]]
   profile={}
   for key in {k for p in previous for k in p["stats"]}:
    observed=[p["stats"][key] for p in previous if key in p["stats"]]
    if len(observed)>=3:profile[key]=round(sum(observed)/len(observed),4)
   if profile:snapshots.setdefault(game["game_id"],{})[tid]=profile
 target=ROOT/f"cbb/match-lab/data/box-pregame-{year}.json"
 target.write_text(json.dumps({"season":year,"source":"CBBD /games/teams","games":snapshots},separators=(",",":"))+"\n")
 print(f"season {year}: {len(snapshots)} game IDs with authentic earlier-game averages")
if __name__=="__main__":main()
