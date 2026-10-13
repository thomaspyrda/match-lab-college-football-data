#!/usr/bin/env python3
"""Two research-only BetWise dominance weight mixes; descriptive, no spread predictions."""
import csv,json,statistics
from collections import defaultdict
from pathlib import Path
import test_pure_units_expected_residual as b
D=Path("data/research/2026")
teams=sorted(b.m.teams)
games=list(csv.DictReader((D/"market_line_games.csv").open()))
market=json.loads((D/"market_no_preseason_comparison.json").read_text())["variants"]["market_only"]
market_power={v["team"]:v["power"] for v in market}
def standardize(values):
 mu=statistics.fmean(values.values());sd=statistics.pstdev(values.values()) or 1.
 return {t:(v-mu)/sd for t,v in values.items()}
market_z=standardize(market_power)
# Four pure-unit season performance relative to opponent's frozen pregame quality.
unit_component=standardize({t:statistics.fmean(b.raw[t].values()) for t in teams})
# Competition recognition is EARNED, not SOS points for merely scheduling opponents.
# Credit strong actual outcomes vs strong opponents; all defeats negative,
# with identical outcome rule regardless of conference.
competition_events=defaultdict(list)
result_events=defaultdict(list)
ats_events=defaultdict(list)
audit=[]
for g in games:
 wk=int(g["week"])
 home,away=g["home"],g["away"]
 if home not in market_z or away not in market_z:continue
 margin=float(g["actual_home_margin"]);residual=float(g["ats_home"])
 for team,opp,signed_margin,signed_ats in [(home,away,margin,residual),(away,home,-margin,-residual)]:
  strength=market_z[opp]
  w=max(.65,min(1.5,1+.25*strength))
  # Earned competition only: a good win against strong opponent scores more.
  # Losing never earns a positive competition score simply for facing a strong opponent.
  quality=(1. if signed_margin>0 else -.7)*w
  competition_events[team].append(quality)
  result_events[team].append(1. if signed_margin>0 else -1.)
  ats_events[team].append((signed_ats,w))
  audit.append({"team":team,"opponent":opp,"week":wk,"opponent_market_z":round(strength,4),"weight":round(w,4),"ats":signed_ats,"win":signed_margin>0,"competition_credit":round(quality,4)})
def avg(seq):return statistics.fmean(seq) if seq else 0.
competition=standardize({t:avg(competition_events[t]) for t in teams})
# Market-based component measures EXCESS vs market, not baseline market rank
# (baseline strength already informs competition weighting).
market_performance=standardize({t:sum(v*w for v,w in ats_events[t])/(sum(w for _,w in ats_events[t])+3) if ats_events[t] else 0. for t in teams})
results=standardize({t:avg(result_events[t]) for t in teams})
components={"four_unit":unit_component,"earned_competition":competition,"ats_market":market_performance,"results":results}
variants={}
for key,weights in {"40_25_25_10":(.40,.25,.25,.10),"50_20_20_10":(.50,.20,.20,.10)}.items():
 rows=[]
 for t in teams:
  score=sum(weight*components[k][t] for k,weight in zip(components,weights))
  rows.append({"team":t,"score_z":round(score,5),"dominance_index":round(50+15*score,2),**{k:round(v[t],4) for k,v in components.items()}})
 rows.sort(key=lambda x:(-x["score_z"],x["team"]))
 for n,r in enumerate(rows,1):r["rank"]=n
 variants[key]=rows
(D/"betwise_dominance_weight_comparison.json").write_text(json.dumps({"model":"Descriptive 4-component dominance; provisional independent z-scaled measures","weight_order":list(components),"weights":{"40_25_25_10":[.40,.25,.25,.10],"50_20_20_10":[.50,.20,.20,.10]},"caveats":["Four-unit opponent adjustments use frozen pregame strengths from prior research model.","Opponent market strength determined from 2026 full-period spreads; used for retrospective ranking only.","Strong-opponent victory recognition and ATS residual can correlate; component overlap needs auditing.","Market component measures ATS residual, NOT absolute market power; no preseason anchor in market-derived opponent weights.","Only completed FBS-versus-FBS games are included; 0–100 display not forced at boundaries."],"variants":variants},indent=2))
with (D/"betwise_dominance_weight_comparison.csv").open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["model","rank","team","dominance_index","score_z","four_unit","earned_competition","ats_market","results"])
 for model,rows in variants.items():
  for r in rows:w.writerow([model,r["rank"],r["team"],r["dominance_index"],r["score_z"],r["four_unit"],r["earned_competition"],r["ats_market"],r["results"]])
(D/"betwise_dominance_game_audit.json").write_text(json.dumps(audit,indent=2))
print("BetWise composite weights:",[(v,[(r["rank"],r["team"]) for r in rows[:25]]) for v,rows in variants.items()])
