"""Reconstruct CBB game-level shooting, rebounding and assist profiles from CBBD.
Requires CBBD_API_KEY in Actions secrets. Outputs a compact, per-game snapshot index.
No season-ending averages, rankings, or missing-value zeros are introduced.
"""
import argparse,json,os,math
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timedelta,timezone


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
  for fieldname in ((field,) if field!="total" else ("total","value","count")):
   if fieldname in item:
    found=v(item[fieldname])
    if found is not None:return found
 return None
def derive(r):
 own=r.get("teamStats") or {};opp=r.get("opponentStats") or {}
 # Require numerical make/attempt pairs: never use missing as zero.
 def made_attempt(stats,kind):
  s=stats.get(kind) or {}
  m=v(s.get("made") if s.get("made") is not None else s.get("makes"));a=v(s.get("attempted") if s.get("attempted") is not None else s.get("attempts"))
  return (m,a) if m is not None and a is not None and a>=0 and 0<=m<=a else (None,None)
 fg, fga=made_attempt(own,"fieldGoals");th,tha=made_attempt(own,"threePointFieldGoals")
 ofg,ofga=made_attempt(opp,"fieldGoals");oth,otha=made_attempt(opp,"threePointFieldGoals")
 ft,fta=made_attempt(own,"freeThrows")
 values={"oreb_pg":measure(r,"teamStats","rebounds","offensive"),"dreb_pg":measure(r,"teamStats","rebounds","defensive"),
  "assists_pg":measure(r,"teamStats","assists"),"opp_assists_pg":measure(r,"opponentStats","assists"),
  "pace":v(r.get("pace")),"turnovers":measure(r,"teamStats","turnovers"),
  "opponent_turnovers":measure(r,"opponentStats","turnovers")}
 if None not in (th,tha) and tha>0:values["three_pct"]=100*th/tha
 if None not in (oth,otha) and otha>0:values["opp_three_pct"]=100*oth/otha
 if None not in (fg,fga,th) and fga>0:values["efg_pct"]=100*(fg+0.5*th)/fga
 if None not in (ofg,ofga,oth) and ofga>0:values["opp_efg_pct"]=100*(ofg+0.5*oth)/ofga
 if None not in (ft,fta) and fta>0:values["ft_pct"]=100*ft/fta
 if values["turnovers"] is not None and values["opponent_turnovers"] is not None:
  values["turnover_margin"]=values["opponent_turnovers"]-values["turnovers"]
 for key,n in {"_fg_m":fg,"_fg_a":fga,"_three_m":th,"_three_a":tha,
  "_opp_fg_m":ofg,"_opp_fg_a":ofga,"_opp_three_m":oth,"_opp_three_a":otha,"_ft_m":ft,"_ft_a":fta,
  "_points":measure(r,"teamStats","points"),"_opp_points":measure(r,"opponentStats","points"),
  "_poss":v(own.get("possessions")),"_opp_poss":v(opp.get("possessions"))}.items():
  if n is not None:values[key]=n
 return {k:round(n,5) for k,n in values.items() if n is not None}

def aggregate(previous):
 """One prior game is valid; require complete prior-game coverage per metric."""
 if not previous:return {}
 count=len(previous);profile={}
 rates={"three_pct","opp_three_pct","efg_pct","opp_efg_pct","ft_pct"}
 keys={k for p in previous for k in p["stats"] if not k.startswith("_")}-rates
 for key in keys:
  observed=[p["stats"][key] for p in previous if key in p["stats"]]
  if len(observed)==count:profile[key]=round(sum(observed)/count,4)
 def total(key):
  values=[p["stats"].get(key) for p in previous]
  return sum(values) if all(n is not None for n in values) else None
 for key,made,attempted in [("three_pct","_three_m","_three_a"),("opp_three_pct","_opp_three_m","_opp_three_a"),("ft_pct","_ft_m","_ft_a")]:
  m,a=total(made),total(attempted)
  if m is not None and a is not None and a>0:profile[key]=round(100*m/a,4)
 for key,prefix in [("efg_pct",""),("opp_efg_pct","opp_")]:
  m,a,th=total("_"+prefix+"fg_m"),total("_"+prefix+"fg_a"),total("_"+prefix+"three_m")
  if None not in (m,a,th) and a>0:profile[key]=round(100*(m+.5*th)/a,4)
 for key,points,poss in [("off_eff","_points","_poss"),("def_eff","_opp_points","_opp_poss")]:
  p,n=total(points),total(poss)
  if p is not None and n is not None and n>0:profile[key]=round(100*p/n,4)
 if profile:
  profile["box_stat_games"]=count
  profile["box_stats_as_of"]=max(p["date"] for p in previous)
 return profile

def snapshots_for_team(expected,observed):
 snapshots={}
 for gid,target in expected.items():
  prior=[{"game_id":pid,"date":g["date"],"stats":observed.get(pid,{}).get("stats",{})}
         for pid,g in expected.items() if g["date"][:10]<target["date"][:10]]
  profile=aggregate(prior)
  if profile:snapshots[gid]=profile
 return snapshots

def main():
 parser=argparse.ArgumentParser();parser.add_argument("--season",type=int,required=True)
 args=parser.parse_args()
 if not os.getenv("CBBD_API_KEY"):raise SystemExit("CBBD_API_KEY Actions secret required")
 from backfill_cbb_cbdd_history import window
 year=args.season
 first=datetime(year-1,10,1,tzinfo=timezone.utc);last=datetime(year,5,31,23,59,59,tzinfo=timezone.utc)
 byteam=defaultdict(dict)
 registry=json.loads((ROOT/"data/sports/team-registry.json").read_text())["teams"]
 espn_games=defaultdict(dict);expected=defaultdict(dict)
 for school in registry:
  if school.get("sport")!="cbb":continue
  path=ROOT/f"data/cbb/teams/{school['slug']}.json"
  if not path.exists():continue
  archive=json.loads(path.read_text()).get("seasons",{}).get(str(year),{})
  tid=str(school["espn_id"])
  for phase in archive.get("phases",{}).values():
   for game in phase.get("games",[]):
    if str(game.get("status","")).lower() not in ("final","completed"):continue
    points,against=v(game.get("points")),v(game.get("opponent_points"))
    gid=str(game.get("id") or "");date=game.get("date")
    if not gid or not date or points is None or against is None:continue
    record={"date":date,"points":points,"against":against}
    espn_games[gid][tid]=record;expected[tid][gid]=record
 cur=first
 while cur<=last:
  stop=min(last,cur+timedelta(days=30))
  games=window("/games",year,cur,stop)
  dates={str(g.get("id") or g.get("gameId")):g.get("startDate") or g.get("startTime") for g in games}
  crosswalk={}
  for g in games:
   if g.get("status")!="final":continue
   cbid=str(g.get("id") or g.get("gameId") or "");source=str(g.get("sourceId") or "")
   if not cbid or not source:continue
   for eid,archived in espn_games.get(source,{}).items():
    for own,opp,key in ((g.get("homePoints"),g.get("awayPoints"),"homeTeamId"),(g.get("awayPoints"),g.get("homePoints"),"awayTeamId")):
     if archived["points"]==own and archived["against"]==opp and own!=opp and g.get(key) is not None:
      crosswalk[(cbid,str(g[key]))]=(source,eid)
  for row in window("/games/teams",year,cur,stop):
   gid=str(row.get("gameId") or "");tid=str(row.get("teamId") or "")
   started=row.get("startDate") or dates.get(gid)
   mapped=crosswalk.get((gid,tid))
   if not gid or not tid or not started or not mapped:continue
   espn_game,espn_team=mapped
   archive=expected[espn_team][espn_game]
   if measure(row,"teamStats","points")!=archive["points"] or measure(row,"opponentStats","points")!=archive["against"]:continue
   values=derive(row)
   byteam[espn_team][espn_game]={"game_id":espn_game,"date":started,"stats":values}
  cur=stop+timedelta(microseconds=1)
 snapshots={}
 for tid,targets in expected.items():
  for gid,profile in snapshots_for_team(targets,byteam.get(tid,{})).items():
   snapshots.setdefault(gid,{})[tid]=profile
 target=ROOT/f"cbb/match-lab/data/box-pregame-{year}.json"
 target.write_text(json.dumps({"season":year,"source":"CBBD /games/teams","games":snapshots},separators=(",",":"))+"\n")
 from collections import Counter
 coverage=Counter(k for teams in snapshots.values() for profile in teams.values() for k in profile)
 print(f"season {year}: {len(snapshots)} game IDs with authentic earlier-game averages")
 print("Metric observations:",dict(sorted(coverage.items())))
if __name__=="__main__":main()
