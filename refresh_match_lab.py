#!/usr/bin/env python3
import csv,json,os,urllib.parse,urllib.request
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parent; DATA=ROOT/"data"; (DATA/"historical").mkdir(parents=True,exist_ok=True)
KEY=os.environ.get("CFBD_API_KEY")
if not KEY: raise SystemExit("CFBD_API_KEY secret is required")
def api(path,**params):
 url="https://api.collegefootballdata.com"+path+"?"+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"MatchLab/1.0"})
 with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
def dt(v):
 try:return datetime.fromisoformat((v or "").replace("Z","+00:00"))
 except:return datetime.min.replace(tzinfo=timezone.utc)
def pickline(entry):
 providers=entry.get("lines") or []
 pref=next((x for x in providers if str(x.get("provider","")).lower()=="consensus"),None)
 return pref or next((x for x in providers if x.get("spread") is not None or x.get("overUnder") is not None),None) or (providers[0] if providers else {})
def num(v):
 try:return float(v) if v is not None else None
 except:return None
def result(team,g):
 hp=g.get("homePoints");ap=g.get("awayPoints")
 if hp is None or ap is None:return None
 home=g.get("homeTeam")==team; won=(hp>ap) if home else (ap>hp)
 return {"won":won,"points":hp if home else ap,"allowed":ap if home else hp}
def form(team,prior):
 rr=[result(team,g) for g in prior[-5:]];rr=[x for x in rr if x]
 return {"games":len(rr),"wins":sum(x["won"] for x in rr),"losses":sum(not x["won"] for x in rr),"avg_points":round(sum(x["points"] for x in rr)/len(rr),1) if rr else None,"avg_allowed":round(sum(x["allowed"] for x in rr)/len(rr),1) if rr else None,"coming_off_loss":(not rr[-1]["won"]) if rr else None}
strength={}
for p in (DATA/"weekly").glob("*.json"):
 d=json.loads(p.read_text());strength[int(d["season"])]=d["weeks"]
def srank(year,week,team):
 r=strength.get(year,{}).get(str(week),{}).get("teams",{}).get(team,{})
 return {k:r.get(k) for k in ("ap_rank","national_strength_rank","fbs_field_size","strength_score","strength_tier","top_percent")}
all_upcoming=[]; now=datetime.now(timezone.utc); end=now+timedelta(days=7)
for year in sorted(strength):
 games=api("/games",year=year,seasonType="regular")
 lines=api("/lines",year=year,seasonType="regular")
 lm={str(x.get("id")):pickline(x) for x in lines}
 histories=defaultdict(list); records=[]
 for g in sorted(games,key=lambda x:dt(x.get("startDate"))):
  gid=str(g.get("id"));week=int(g.get("week") or 0);home=g.get("homeTeam");away=g.get("awayTeam")
  if not home or not away:continue
  line=lm.get(gid,{})
  hs=srank(year,week,home);as_=srank(year,week,away)
  if hs.get("national_strength_rank") is None or as_.get("national_strength_rank") is None:continue
  hf=form(home,histories[home]);af=form(away,histories[away])
  spread=num(line.get("spread"));total=num(line.get("overUnder"));hml=num(line.get("homeMoneyline"));aml=num(line.get("awayMoneyline"))
  hp=g.get("homePoints");ap=g.get("awayPoints");completed=hp is not None and ap is not None
  fav_side=None
  if spread is not None:fav_side="home" if spread<0 else ("away" if spread>0 else None)
  ats=None
  if completed and spread is not None:
   adj=float(hp)+spread-float(ap);ats="home_cover" if adj>0 else ("away_cover" if adj<0 else "push")
  ou=None
  if completed and total is not None:
   s=float(hp)+float(ap);ou="over" if s>total else ("under" if s<total else "push")
  rec={"game_id":gid,"season":year,"week":week,"start_date":g.get("startDate"),"home":home,"away":away,"home_conference":g.get("homeConference"),"away_conference":g.get("awayConference"),"conference_game":bool(g.get("conferenceGame")),"neutral_site":bool(g.get("neutralSite")),"spread":spread,"over_under":total,"home_moneyline":hml,"away_moneyline":aml,"provider":line.get("provider"),"home_profile":hs|{"recent_form":hf},"away_profile":as_|{"recent_form":af},"favorite_side":fav_side,"result":{"home_points":hp,"away_points":ap,"ats":ats,"total":ou} if completed else None}
  records.append(rec)
  kickoff=dt(g.get("startDate"))
  if year==now.year and now<=kickoff<=end: all_upcoming.append(rec|{"result":None})
  if completed:histories[home].append(g);histories[away].append(g)
 (DATA/"historical"/f"{year}.json").write_text(json.dumps({"season":year,"games":records},separators=(",",":")),encoding="utf-8")
(DATA/"upcoming.json").write_text(json.dumps({"generated_at":now.isoformat(),"window_end":end.isoformat(),"games":sorted(all_upcoming,key=lambda x:x["start_date"] or "")},indent=2),encoding="utf-8")
print(f"Published {len(all_upcoming)} upcoming games and historical indexes for {len(strength)} seasons")
