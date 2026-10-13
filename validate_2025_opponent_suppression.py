#!/usr/bin/env python3
"""2025 out-of-sample suppression validation. Pregame snapshot W-1 predicts game W.
Compare 0/35/50/65 using Pearson correlation, Spearman rank correlation and
holdout standardized residual prediction. No in-sample model selection.
"""
import csv,json,math,statistics
from pathlib import Path
from collections import defaultdict
P=Path("data/research/2025")
R=list(csv.DictReader((P/"opponent_unit_suppression_weekly_comparison.csv").open()))
K=("PO","PD","RO","RD");AMP=(0.,.35,.5,.65)
ratings={(int(x["through_week"]),x["team"],x["unit"],float(x["max_suppression"])):float(x["z"]) for x in R}
G=list(csv.DictReader((P/"weekly_team_metrics.csv").open()))
teams={x["team"] for x in R}
games=[g for g in G if g["fbs_opponent"]=="1" and g["team"] in teams and g["opponent"] in teams]
M={"PO":[("passing_ppa",.4),("passing_success",.4),("passing_20plus_rate",.2)],
"PD":[("passing_ppa",.4),("passing_success",.4),("passing_20plus_rate",.2)],
"RO":[("rushing_success",.25),("rushing_ppa",.2),("stuff_avoidance",.17),("line_yards",.14),("power_success",.11),("second_level_yards",.08),("open_field_yards",.05)],
"RD":[("rushing_success",.25),("rushing_ppa",.2),("stuff_avoidance",.17),("line_yards",.14),("power_success",.11),("second_level_yards",.08),("open_field_yards",.05)]}
def n(x):
 try:return float(x)
 except:return None
def corr(x,y):
 if len(x)<3:return 0
 mx,my=statistics.fmean(x),statistics.fmean(y)
 den=math.sqrt(sum((v-mx)**2 for v in x)*sum((v-my)**2 for v in y))
 return sum((a-mx)*(b-my) for a,b in zip(x,y))/den if den else 0.
def rank(x):
 order=sorted(range(len(x)),key=lambda i:x[i]);r=[0.]*len(x);i=0
 while i<len(x):
  j=i+1
  while j<len(x) and x[order[j]]==x[order[i]]:j+=1
  for k in range(i,j):r[order[k]]=(i+j+1)/2
  i=j
 return r
# Evaluation weeks 3+ to avoid a one-game prior-week snapshot when possible.
obs=defaultdict(list)
for week in sorted({int(g["week"]) for g in games}):
 if week<3:continue
 past=[g for g in games if int(g["week"])<week]
 baselines={}
 for side in ("off","def"):
  for metric in {m for spec in M.values() for m,_ in spec}:
   vals=[n(g.get(side+"_"+metric)) for g in past]
   vals=[v for v in vals if v is not None]
   if len(vals)>=30:baselines[side,metric]=(statistics.fmean(vals),statistics.pstdev(vals) or 1.)
 for g in games:
  if int(g["week"])!=week:continue
  t=g["team"]
  for k in K:
   side="off" if k in ("PO","RO") else "def";parts=[]
   for metric,w in M[k]:
    v=n(g.get(side+"_"+metric))
    if v is None or (side,metric) not in baselines:continue
    mu,sd=baselines[side,metric]
    parts.append((((v-mu)/sd)*(-1 if side=="def" else 1),w))
   if not parts:continue
   measured=sum(v*w for v,w in parts)/sum(w for _,w in parts)
   if all((week-1,t,k,a) in ratings for a in AMP):
    obs[k].append((week,t,measured,*[ratings[week-1,t,k,a] for a in AMP]))
out={"method":"Week W-1 frozen strengths predict Week W game-specific raw four-unit performance, W>=3; baseline game metric z-scales from games before Week W; FBS-only. Correlation and Spearman compare 0%,35%,50%,65%. Raw observed game statistics themselves not adjusted. This is predictive association, not definitive calibration or a betting backtest.","units":{},"leaders":{}}
for k in K:
 a=obs[k];actual=[x[2] for x in a];out["units"][k]={"observations":len(a)}
 for j,amp in enumerate(AMP):
  predicted=[x[3+j] for x in a]
  out["units"][k][str(int(amp*100))]={"pearson":round(corr(predicted,actual),5),"spearman":round(corr(rank(predicted),rank(actual)),5)}
last=max(int(x["through_week"]) for x in R)
for k in K:
 out["leaders"][k]={}
 for amp in AMP:
  top=sorted((x for x in R if int(x["through_week"])==last and x["unit"]==k and float(x["max_suppression"])==amp),key=lambda x:int(x["rank"]))[:15]
  out["leaders"][k][str(int(amp*100))]=[{"team":x["team"],"rank":int(x["rank"]),"rating":float(x["rating"])} for x in top]
watch=("Florida International","Liberty","Georgia State","Oregon State","Georgia","Notre Dame","Oregon","James Madison")
out["tracked"]={t:{k:{str(int(a*100)):{"rank":int(x["rank"]),"rating":float(x["rating"])} for a in AMP for x in R if int(x["through_week"])==last and x["team"]==t and x["unit"]==k and float(x["max_suppression"])==a} for k in K} for t in watch}
scores={}
for amp in AMP:
 key=str(int(amp*100));scores[key]=round(statistics.fmean(out["units"][k][key]["pearson"] for k in K),5)
out["mean_pearson"]=scores
out["best_mean_pearson"]=max(scores,key=scores.get)
(P/"opponent_unit_suppression_2025_validation.json").write_text(json.dumps(out,indent=2))
print("2025 forward unit validation",json.dumps({"units":out["units"],"mean_pearson":scores,"best":out["best_mean_pearson"]}),flush=True)
