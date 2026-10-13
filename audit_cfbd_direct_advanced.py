#!/usr/bin/env python3
"""Research-only source parity audit: CFBD's cumulative season advanced stats.
No production writes, no modification of historical v1/weekly four-unit archives.
CFBD_API_KEY is supplied by existing GitHub Actions secret.
"""
import csv,json,os,time,urllib.request,urllib.parse,urllib.error,statistics,math
from pathlib import Path
from collections import defaultdict
ROOT=Path("data/research")
KEY=os.getenv("CFBD_API_KEY")
if not KEY:raise SystemExit("Missing CFBD_API_KEY")
ALIASES={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
def canon(x):return ALIASES.get(x,x)
def fetch(year,week,garbage):
 args={"year":year,"startWeek":1,"endWeek":week,"classification":"fbs","excludeGarbageTime":str(garbage).lower()}
 url="https://api.collegefootballdata.com/stats/season/advanced?"+urllib.parse.urlencode(args)
 for retry in range(4):
  try:
   req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json"})
   with urllib.request.urlopen(req,timeout=120) as resp:return json.load(resp)
  except Exception:
   if retry==3:raise
   time.sleep(2**retry)
def num(x):
 try:
  v=float(x)
  return v if math.isfinite(v) else None
 except (TypeError,ValueError):return None
def fields(obj,side,kind):
 s=obj.get(side) or {}; p=s.get(kind+"Plays") or {}
 return {k:num(p.get(k)) for k in ("ppa","successRate","explosiveness","totalPPA","rate")}
def main():
 for year in (2025,2026):
  folder=ROOT/str(year)
  weeks=sorted({int(r["week"]) for r in csv.DictReader((folder/"weekly_team_metrics.csv").open())})
  teams=set(json.loads((folder/"conference_membership.json").read_text())["teams"])
  out=[];alerts=[]
  blocked=None
  for week in weeks:
   if blocked:break
   for garbage in ([True,False] if year==2026 and week==6 else [True]):
    try:
     response=fetch(year,week,garbage)
    except urllib.error.HTTPError as exc:
     if exc.code not in (401,403):raise
     blocked={"code":exc.code,"endpoint":"/stats/season/advanced","explanation":"Season advanced endpoint rejected the existing CFBD credential. The game advanced endpoint succeeds earlier in this workflow; do not presume a missing key. Check endpoint entitlement and account/API authorization.","failed_week":week,"exclude_garbage_time":garbage}
     print("CFBD SEASON ADVANCED ACCESS BLOCKED",year,blocked,flush=True)
     break
    if not isinstance(response,list):raise RuntimeError("Unexpected API response")
    found=set()
    for row in response:
     t=canon(row.get("team") or "")
     if t not in teams:continue
     if t in found:raise RuntimeError("duplicate team "+t)
     found.add(t)
     entry={"season":year,"through_week":week,"team":t,"exclude_garbage_time":str(garbage).lower()}
     for side in ("offense","defense"):
      for kind in ("passing","rushing"):
       for k,v in fields(row,side,kind).items():entry[side+"_"+kind+"_"+k]=v
     out.append(entry)
    if len(found)<120:raise RuntimeError(f"Incomplete API response for {year} week {week}: {len(found)}")
    alerts.append({"season":year,"week":week,"exclude_garbage_time":garbage,"teams":len(found),"missing_fbs":sorted(teams-found)})
  dest=folder/"cfbd_direct_season_advanced_weekly.csv"
  if out and not blocked:
   with dest.open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
  (folder/"cfbd_direct_season_advanced_coverage.json").write_text(json.dumps({"endpoint":"/stats/season/advanced","query":{"startWeek":1,"classification":"fbs"},"source":"CFBD direct API","coverage":alerts,"blocked":blocked,"status":"blocked_unauthorized" if blocked else "success",
   "warning":"This is direct season-to-week aggregated CFBD data, not proof of Fourth and Short site parity. Classification filters team classification; opponent FBS-only exclusions are not guaranteed.","existing_files_untouched":True},indent=2))
  print("Direct CFBD advanced",year,"rows",len(out),"weeks",len(weeks),"status",("blocked" if blocked else "success"),flush=True)
if __name__=="__main__":main()
