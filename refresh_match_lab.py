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
 rr=[result(team,g) for g in prior];rr=[x for x in rr if x]
 return {"games":len(rr),"wins":sum(x["won"] for x in rr),"losses":sum(not x["won"] for x in rr),"avg_points":round(sum(x["points"] for x in rr)/len(rr),1) if rr else None,"avg_allowed":round(sum(x["allowed"] for x in rr)/len(rr),1) if rr else None,"coming_off_loss":(not rr[-1]["won"]) if rr else None}
strength={}
for p in (DATA/"weekly").glob("*.json"):
 d=json.loads(p.read_text());strength[int(d["season"])]=d["weeks"]
advanced={}
for p in (DATA/"profiles").glob("*.json"):
 d=json.loads(p.read_text());advanced[int(d["season"])]=d.get("weeks",{})
def srank(year,week,team):
 r=strength.get(year,{}).get(str(week),{}).get("teams",{}).get(team,{})
 return {k:r.get(k) for k in ("ap_rank","national_strength_rank","fbs_field_size","strength_score","strength_tier","top_percent")}
def adv(year,week,team):
 board=advanced.get(year,{}).get(str(week),{})
 r=board.get("teams",{}).get(team)
 return (r|{"through_week":board.get("through_week")}) if r else None
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
  if hs.get("national_strength_rank") is None and as_.get("national_strength_rank") is None:continue
  hs["classification"]="FBS" if hs.get("national_strength_rank") is not None else "FCS/Other"
  as_["classification"]="FBS" if as_.get("national_strength_rank") is not None else "FCS/Other"
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
  rec={"game_id":gid,"season":year,"week":week,"start_date":g.get("startDate"),"home":home,"away":away,"home_id":g.get("homeId"),"away_id":g.get("awayId"),"home_conference":g.get("homeConference"),"away_conference":g.get("awayConference"),"conference_game":bool(g.get("conferenceGame")),"neutral_site":bool(g.get("neutralSite")),"spread":spread,"over_under":total,"home_moneyline":hml,"away_moneyline":aml,"provider":line.get("provider"),"home_profile":hs|{"recent_form":hf,"advanced":adv(year,week,home)},"away_profile":as_|{"recent_form":af,"advanced":adv(year,week,away)},"favorite_side":fav_side,"result":{"home_points":hp,"away_points":ap,"ats":ats,"total":ou} if completed else None}
  records.append(rec)
  kickoff=dt(g.get("startDate"))
  if year==now.year and now<=kickoff<=end: all_upcoming.append(rec|{"result":None})
  if completed:histories[home].append(g);histories[away].append(g)
 (DATA/"historical"/f"{year}.json").write_text(json.dumps({"season":year,"games":records},separators=(",",":")),encoding="utf-8")
# CFBD's season-wide games response may omit future weeks. Request the next
# two weeks explicitly, then build their live AP and full-field strength boards.
current_records=json.loads((DATA/"historical"/f"{now.year}.json").read_text())["games"]
next_week=max((g["week"] for g in current_records),default=0)+1
rankings=api("/rankings",year=now.year,seasonType="regular")
def live_ap(week):
 snap=next((x for x in rankings if int(x.get("week") or 0)==week),None)
 poll=next((p for p in (snap or {}).get("polls",[]) if str(p.get("poll","")).lower() in ("ap top 25","ap")),None)
 return {r.get("school"):int(r["rank"]) for r in (poll or {}).get("ranks",[]) if r.get("school")}
def live_strength(week):
 ratings=api("/ratings/elo",year=now.year,seasonType="regular",week=week)
 vals=[]
 for r in ratings:
  team=r.get("team") or r.get("school"); value=r.get("elo")
  if team and value is not None: vals.append((team,int(value)))
 vals.sort(key=lambda x:(-x[1],x[0])); ap=live_ap(week); out={}; last=None; rank=0
 for pos,(team,value) in enumerate(vals,1):
  if value!=last:rank=pos;last=value
  below=sum(v<value for _,v in vals); tied=sum(v==value for _,v in vals)
  pct=100 if len(vals)<=1 else 100*(below+(tied-1)/2)/(len(vals)-1)
  score=max(1,min(100,int(pct+0.5)))
  out[team]={"ap_rank":ap.get(team),"national_strength_rank":rank,"fbs_field_size":len(vals),"strength_score":score,"strength_tier":"Elite" if score>=90 else "Strong" if score>=75 else "Above Average" if score>=50 else "Below Average" if score>=25 else "Weak","top_percent":101-score}
 return out
all_upcoming=[]
for week in (next_week,next_week+1):
 future=api("/games",year=now.year,seasonType="regular",week=week)
 future_lines=api("/lines",year=now.year,seasonType="regular",week=week)
 fl={str(x.get("id")):pickline(x) for x in future_lines}; board=live_strength(week)
 for g in future:
  kickoff=dt(g.get("startDate"))
  if not (now<=kickoff<=end):continue
  home=g.get("homeTeam");away=g.get("awayTeam");line=fl.get(str(g.get("id")),{})
  hp=board.get(home,{});ap=board.get(away,{})
  if hp.get("national_strength_rank") is None and ap.get("national_strength_rank") is None: continue
  hp["classification"]="FBS" if hp.get("national_strength_rank") is not None else "FCS/Other"
  ap["classification"]="FBS" if ap.get("national_strength_rank") is not None else "FCS/Other"
  home_prior=[x for x in games if (x.get("homeTeam")==home or x.get("awayTeam")==home) and x.get("homePoints") is not None and dt(x.get("startDate"))<kickoff]
  away_prior=[x for x in games if (x.get("homeTeam")==away or x.get("awayTeam")==away) and x.get("homePoints") is not None and dt(x.get("startDate"))<kickoff]
  all_upcoming.append({"game_id":str(g.get("id")),"season":now.year,"week":week,"start_date":g.get("startDate"),"home":home,"away":away,"home_id":g.get("homeId"),"away_id":g.get("awayId"),"home_conference":g.get("homeConference"),"away_conference":g.get("awayConference"),"conference_game":bool(g.get("conferenceGame")),"neutral_site":bool(g.get("neutralSite")),"spread":num(line.get("spread")),"over_under":num(line.get("overUnder")),"home_moneyline":num(line.get("homeMoneyline")),"away_moneyline":num(line.get("awayMoneyline")),"provider":line.get("provider"),"home_profile":hp|{"recent_form":form(home,home_prior),"advanced":adv(now.year,week,home)},"away_profile":ap|{"recent_form":form(away,away_prior),"advanced":adv(now.year,week,away)},"favorite_side":"home" if num(line.get("spread")) is not None and num(line.get("spread"))<0 else ("away" if num(line.get("spread")) is not None and num(line.get("spread"))>0 else None),"result":None})
(DATA/"upcoming.json").write_text(json.dumps({"generated_at":now.isoformat(),"window_end":end.isoformat(),"games":sorted(all_upcoming,key=lambda x:x["start_date"] or "")},indent=2),encoding="utf-8")
print(f"Published {len(all_upcoming)} upcoming games and historical indexes for {len(strength)} seasons")
