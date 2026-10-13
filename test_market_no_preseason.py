#!/usr/bin/env python3
"""Research: verify historical CFBD closing-line fields and compare market ratings."""
import csv,json,os,statistics,urllib.request,urllib.parse,time
from collections import defaultdict,Counter
from pathlib import Path
D=Path("data/research/2026");key=os.getenv("CFBD_API_KEY")
if not key:raise RuntimeError("CFBD_API_KEY missing")
games=list(csv.DictReader((D/"games.csv").open()))
teams=sorted({r["team"] for r in csv.DictReader((D/"weekly_team_metrics.csv").open())})
def query(week):
 url="https://api.collegefootballdata.com/lines?"+urllib.parse.urlencode({"year":2026,"week":week,"seasonType":"regular"})
 for trial in range(4):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={"Authorization":"Bearer "+key}),timeout=120) as r:return json.load(r)
  except Exception:
   if trial==3:raise
   time.sleep(2**trial)
line_by_id={}
for week in sorted({int(g["week"]) for g in games}):
 for item in query(week):
  offers=[]
  for line in item.get("lines") or []:
   try:spread=float(line["spread"])
   except (ValueError,TypeError,KeyError):continue
   provider=str(line.get("provider") or "")
   priority={"consensus":0,"draftkings":1,"caesars":2}.get(provider.lower(),9)
   offers.append((priority,provider,spread))
  if offers:
   _,provider,spread=min(offers)
   line_by_id[str(item.get("id") or item.get("gameId"))]=(provider,spread)
matched=[];missing=[]
for g in games:
 if g["home"] not in teams or g["away"] not in teams:continue
 offer=line_by_id.get(g["game_id"])
 if offer is None:
  missing.append({"game_id":g["game_id"],"home":g["home"],"away":g["away"]});continue
 provider,spread=offer
 margin=int(g["home_points"])-int(g["away_points"])
 matched.append({"week":g["week"],"game_id":g["game_id"],"home":g["home"],"away":g["away"],"home_spread":spread,"provider":provider,"actual_home_margin":margin,"expected_home_margin":-spread,"ats_home":margin+spread})
with (D/"market_closing_line_coverage.json").open("w") as f:json.dump({"matched":len(matched),"missing_count":len(missing),"missing":missing,"provider_counts":dict(Counter(x["provider"] for x in matched)),"warning":"CFBD spread field is not guaranteed to represent a timestamp-verified closing line; do not certify closing status without provenance."},f,indent=2)
with (D/"market_line_games.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=["week","game_id","home","away","home_spread","provider","actual_home_margin","expected_home_margin","ats_home"]);w.writeheader();w.writerows(matched)
if len(matched)<30:raise RuntimeError("Not enough verified pregame spread coverage: "+str(len(matched)))
# No preseason anchor: zero-centered numerical regularization only.
# This is not a prior ranking or team-specific prior.
REGULARIZATION=0.5
schedule=defaultdict(list);ats=defaultdict(list)
for g in matched:
 h,a=g["home"],g["away"];v=g["expected_home_margin"]
 schedule[h].append((a,v-2.5));schedule[a].append((h,-v+2.5))
 ats[h].append(g["ats_home"]);ats[a].append(-g["ats_home"])
r={t:0. for t in teams}
for _ in range(700):
 nxt={t:sum(r[o]+d for o,d in schedule[t])/(REGULARIZATION+len(schedule[t])) for t in teams}
 avg=statistics.fmean(nxt.values());r={t:x-avg for t,x in nxt.items()}
# Weighted ATS residual: opponents with higher frozen pregame strength
# receive more influence, without substituting current/future ranks.
# Opponent weights derive exclusively from the fitted market-spread network.
market_mu=statistics.fmean(r.values())
market_sd=statistics.pstdev(r.values()) or 1.
weighted=defaultdict(list)
for g in matched:
 wk=int(g["week"]);h,a=g["home"],g["away"]
 for team,opp,value in [(h,a,g["ats_home"]),(a,h,-g["ats_home"])]:
  strength=(r[opp]-market_mu)/market_sd
  weight=max(.65,min(1.5,1+.25*strength))
  weighted[team].append((value,weight))
variants={}
for name,coef,kind in [("market_only",0,"raw"),("ats_unweighted_0p5",.5,"raw"),("ats_weighted_0p5",.5,"weighted")]:
 ratings={t:r[t]+coef*(sum(v*w for v,w in weighted[t])/(sum(w for _,w in weighted[t])+3) if kind=="weighted" else sum(ats[t])/(len(ats[t])+3)) for t in teams}
 ordered=sorted(teams,key=lambda t:(-ratings[t],t))
 variants[name]=[{"rank":i+1,"team":t,"power":round(ratings[t],4),"market_base":round(r[t],4),"games":len(ats[t]),"mean_ats":round(statistics.fmean(ats[t]),3) if ats[t] else None} for i,t in enumerate(ordered)]
(D/"market_no_preseason_comparison.json").write_text(json.dumps({"warning":"Lines sourced from CFBD spread fields; closing status not verified by timestamp","assumptions":{"home_field_points":2.5,"zero_center_regularization":0.5,"preseason_anchor":0,"ats_shrinkage_games":3},"variants":variants},indent=2))
print("Market coverage:",len(matched),"missing",len(missing));print("Top 25:",[(k,[x["team"] for x in v[:25]]) for k,v in variants.items()])
