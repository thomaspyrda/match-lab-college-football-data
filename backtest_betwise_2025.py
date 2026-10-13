#!/usr/bin/env python3
"""Isolated 2025 historical replication of BetWise 25/35/25/15 unit-matched dominance."""
import csv,json,statistics,urllib.request,urllib.parse,time,os
from collections import defaultdict,Counter
from pathlib import Path
import run_four_unit_research as m
import test_pure_units_expected_residual as b
D=Path("data/research/2025");K=("PO","PD","RO","RD");MATCH={"PO":"PD","PD":"PO","RO":"RD","RD":"RO"}
rows=list(csv.DictReader((D/"weekly_team_metrics.csv").open()))
teams=sorted({r["team"] for r in rows})
fbs=[r for r in rows if int(r["fbs_opponent"]) and r["opponent"] in teams]
# Same unit definitions as 2026, but standardize with 2025 game statistics.
b.scales=m.perweek_metric_z(fbs)
for side in ("off","def"):
 vals=[m.num(r.get(side+"_passing_20plus_rate")) for r in fbs]
 vals=[v for v in vals if v is not None]
 if len(vals)<10:raise RuntimeError("Missing 20+ passing rate "+side)
 b.scales[(side,"passing_20plus_rate")]=(statistics.fmean(vals),statistics.pstdev(vals) or 1.)
records=[]
for r in fbs:
 vals={k:(b.pure_rush_measure(r,k) if k in ("RO","RD") else b.pure_pass_measure(r,k)) for k in K}
 if any(v is None for v in vals.values()):continue
 records.append({"team":r["team"],"opponent":r["opponent"],"game_id":r["game_id"],"week":int(r["week"]),"plays":max(1,m.num(r.get("plays_count")) or 1),"values":vals})
by=defaultdict(list)
for r in records:by[r["team"]].append(r)
means={k:{t:statistics.fmean(x["values"][k] for x in by[t]) if by[t] else 0. for t in teams} for k in K}
def standardize(v):
 mu=statistics.fmean(v.values());sd=statistics.pstdev(v.values()) or 1.
 return {t:(x-mu)/sd for t,x in v.items()}
betas={};coeff_audit={};adjusted=defaultdict(lambda:defaultdict(list))
for k in K:
 other=MATCH[k];opmeans=means[other];overall_mu=statistics.fmean(opmeans.values());overall_sd=statistics.pstdev(opmeans.values()) or 1.
 obs=[]
 for r in records:
  opponents=[z["values"][other] for z in by[r["opponent"]] if z["game_id"]!=r["game_id"]]
  if len(opponents)<2:continue
  opp_z=(statistics.fmean(opponents)-overall_mu)/overall_sd
  obs.append((r["team"],opp_z,r["values"][k]-means[k][r["team"]]))
 avg={t:statistics.fmean(v for team,v,_ in obs if team==t) for t in {x[0] for x in obs}}
 num=sum((v-avg[t])*y for t,v,y in obs);den=sum((v-avg[t])**2 for t,v,y in obs)
 slope=num/den if den else 0.
 betas[k]=max(0.,min(1.5,-slope))
 coeff_audit[k]={"estimated_slope":round(slope,6),"adjustment_beta":round(betas[k],6),"team_games":len(obs),"opposing_unit":other}
 for r in records:
  opponents=[z["values"][other] for z in by[r["opponent"]] if z["game_id"]!=r["game_id"]]
  opponent_value=statistics.fmean(opponents) if len(opponents)>=2 else opmeans[r["opponent"]]
  adj=r["values"][k]+betas[k]*(opponent_value-overall_mu)/overall_sd
  adjusted[r["team"]][k].append((adj,r["plays"]))
def wavg(seq):return sum(v*w for v,w in seq)/sum(w for _,w in seq) if seq else 0.
units={t:{k:wavg(adjusted[t][k]) for k in K} for t in teams}
unit_z=standardize({t:statistics.fmean(units[t].values()) for t in teams})
# Use the same 2026 market dataset source and provider-selection rule.
key=os.getenv("CFBD_API_KEY")
if not key:raise RuntimeError("CFBD_API_KEY required")
def api(week):
 url="https://api.collegefootballdata.com/lines?"+urllib.parse.urlencode({"year":2025,"week":week,"seasonType":"regular"})
 for i in range(4):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={"Authorization":"Bearer "+key}),timeout=120) as f:return json.load(f)
  except Exception:
   if i==3:raise
   time.sleep(2**i)
games=list(csv.DictReader((D/"games.csv").open()))
lines={}
for wk in sorted({int(g["week"]) for g in games}):
 for obj in api(wk):
  offers=[]
  for line in obj.get("lines") or []:
   try:spread=float(line["spread"])
   except (TypeError,ValueError,KeyError):continue
   provider=str(line.get("provider") or "")
   offers.append(({"consensus":0,"draftkings":1,"caesars":2}.get(provider.lower(),9),provider,spread))
  if offers:
   _,provider,spread=min(offers);lines[str(obj.get("id") or obj.get("gameId"))]=(provider,spread)
matched=[];missing=[]
for g in games:
 h,a=g["home"],g["away"]
 if h not in teams or a not in teams:continue
 line=lines.get(g["game_id"])
 if not line:missing.append(g["game_id"]);continue
 provider,sp=line;margin=int(g["home_points"])-int(g["away_points"])
 matched.append({"home":h,"away":a,"week":int(g["week"]),"game_id":g["game_id"],"spread":sp,"margin":margin,"ats":margin+sp,"provider":provider})
if len(matched)<200:raise RuntimeError("Insufficient 2025 market spread coverage "+str(len(matched)))
schedules=defaultdict(list);ats=defaultdict(list)
for g in matched:
 h,a=g["home"],g["away"];expected=-g["spread"]
 schedules[h].append((a,expected-2.5));schedules[a].append((h,-expected+2.5))
 ats[h].append(g["ats"]);ats[a].append(-g["ats"])
rating={t:0. for t in teams}
for _ in range(700):
 nxt={t:sum(rating[o]+margin for o,margin in schedules[t])/(len(schedules[t])+.5) for t in teams}
 mu=statistics.fmean(nxt.values());rating={t:v-mu for t,v in nxt.items()}
market_z=standardize(rating);weighted=defaultdict(list);quality=defaultdict(list);results=defaultdict(list)
for g in matched:
 for t,o,margin,ats_res in [(g["home"],g["away"],g["margin"],g["ats"]),(g["away"],g["home"],-g["margin"],-g["ats"])]:
  w=max(.65,min(1.5,1+.25*market_z[o]))
  weighted[t].append((ats_res,w))
  quality[t].append((1. if margin>0 else -.7)*w)
  results[t].append(1. if margin>0 else -1.)
def avg(x):return statistics.fmean(x) if x else 0.
competition=standardize({t:avg(quality[t]) for t in teams})
result_z=standardize({t:avg(results[t]) for t in teams})
market_component=standardize({t:rating[t]+.5*(sum(x*w for x,w in weighted[t])/(sum(w for _,w in weighted[t])+3) if weighted[t] else 0.) for t in teams})
rankings=[]
for t in teams:
 score=.25*unit_z[t]+.35*competition[t]+.25*market_component[t]+.15*result_z[t]
 rankings.append({"team":t,"score_z":round(score,5),"dominance_index":round(50+15*score,2),"PO":round(units[t]["PO"],4),"PD":round(units[t]["PD"],4),"RO":round(units[t]["RO"],4),"RD":round(units[t]["RD"],4),"four_unit":round(unit_z[t],4),"earned_competition":round(competition[t],4),"market_strength_ats":round(market_component[t],4),"results":round(result_z[t],4)})
rankings.sort(key=lambda x:(-x["score_z"],x["team"]))
for i,r in enumerate(rankings,1):r["rank"]=i
report={"season":2025,"model":"BetWise 2026 latest unit-matched formula replicated with 2025 fitted coefficients","weights":{"four_unit":.25,"earned_competition":.35,"market_strength_ats":.25,"results":.15},"coefficients":coeff_audit,"coverage":{"complete_FBS_team_games":len(records),"completed_FBS_market_matchups":len(matched),"missing_lines":len(missing),"providers":dict(Counter(x["provider"] for x in matched)),"teams":len(teams)},"methodological_notes":["Coefficients refitted using the same algorithm on 2025; NOT copied from 2026.","No preseason anchor in market strength.","Historical unit matched scores are retrospective (season data), not frozen pregame.","Market source spread time-stamp not verified as closing.","Same team unit measurement and metrics as 2026."],"rankings":rankings}
(D/"betwise_unit_matched_2025_backtest.json").write_text(json.dumps(report,indent=2))
with (D/"betwise_unit_matched_2025_backtest.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(rankings[0]));w.writeheader();w.writerows(rankings)
print("2025 backtest coverage",report["coverage"]);print("2025 betas",coeff_audit);print("2025 top 25",[(x["rank"],x["team"]) for x in rankings[:25]])
