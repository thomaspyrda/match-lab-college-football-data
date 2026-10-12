#!/usr/bin/env python3
"""Research-only FBS conference strength and realized conference exposure."""
import csv,json,statistics,math
from collections import defaultdict
from pathlib import Path
D=Path(__file__).resolve().parent/"data"/"research"/"2026"
membership=json.loads((D/"conference_membership.json").read_text())["teams"]
rankings=json.loads((D/"ranking_experiments.json").read_text())["variants"]
reference=rankings["balanced_hybrid_50"]
power={r["team"]:float(r["statistical_strength"]) for r in reference}
games=list(csv.DictReader((D/"weekly_team_metrics.csv").open()))
aliases={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
def canon(x):return aliases.get(x,x)
membership={canon(k):v for k,v in membership.items()}
conf={t:membership.get(t,{}).get("conference","Unknown") for t in power}
def average(vals):return statistics.fmean(vals) if vals else 0.
def std(values):
    mu=average(values);return math.sqrt(average([(v-mu)**2 for v in values])) or 1.
byconference=defaultdict(list)
for t,s in power.items():
    if conf[t] not in ("Independent","Unknown",None,""):
        byconference[conf[t]].append((t,s))
# Cross-conference performance residuals: nonconference games only; measured
# against frozen-independent current ratings solely as descriptive diagnostics.
seen=set();cross=defaultdict(list)
for g in games:
    t=canon(g["team"]);o=canon(g["opponent"])
    if t not in power or o not in power:continue
    if conf.get(t)==conf.get(o):continue
    key=(g["game_id"],t)
    if key in seen:continue
    seen.add(key)
    margin=float(g["team_points"])-float(g["opponent_points"])
    expected=7*(power[t]-power[o])
    cross[conf[t]].append(max(-28,min(28,margin-expected))/28)
# A modest, bounded nonconference factor, with shrinkage to avoid
# disproportionately trusting a tiny number of early-season games.
results=[]
for conference,members in byconference.items():
    ordered=sorted([v for _,v in members],reverse=True)
    n=len(ordered);core=ordered[:min(5,n)]
    middle=ordered[max(0,n//4):max(1,n-math.floor(n/4))]
    cross_games=cross[conference]
    nc=average(cross_games)*min(1,len(cross_games)/12)
    results.append({"conference":conference,"team_count":n,"mean":average(ordered),
      "top5":average(core),"middle50":average(middle),"nonconference_delta":nc,
      "nonconference_team_games":len(cross_games)})
# Normalize across conferences and map into a relative 0-100 score, which
# is descriptive and should not be interpreted as winning probability.
for field in ("mean","top5","middle50","nonconference_delta"):
    vals=[r[field] for r in results];mu=average(vals);sd=std(vals)
    for r in results:r[field+"_z"]=(r[field]-mu)/sd
for r in results:
    r["composite_z"]=.40*r["mean_z"]+.25*r["top5_z"]+.20*r["middle50_z"]+.15*r["nonconference_delta_z"]
zs=[r["composite_z"] for r in results];low=min(zs);high=max(zs)
for r in results:r["conference_strength"]=round(100*(r["composite_z"]-low)/(high-low),2) if high>low else 50.
results.sort(key=lambda r:-r["conference_strength"])
for i,r in enumerate(results,1):r["conference_rank"]=i
# Team exposure: rank actual opponents faced, instead of blanket credit for
# conference affiliation. Current opponent strength is descriptive, NOT pregame.
exposure=defaultdict(list);inconference=defaultdict(list)
for g in games:
    t=canon(g["team"]);o=canon(g["opponent"])
    if t not in power or o not in power:continue
    exposure[t].append(power[o])
    if conf[t]==conf[o]:inconference[t].append(power[o])
ratings=[power[t] for t in power];mu=average(ratings);sd=std(ratings)
teams=[]
for t in sorted(power):
    faced=exposure[t];internal=inconference[t]
    teams.append({"team":t,"conference":conf[t],"overall_opponent_strength":round(average(faced),5) if faced else None,
      "conference_opponent_strength":round(average(internal),5) if internal else None,
      "fbs_games":len(faced),"conference_games":len(internal),
      "relative_opponent_strength_z":round((average(faced)-mu)/sd,4) if faced else None})
teams.sort(key=lambda r: -(r["relative_opponent_strength_z"] if r["relative_opponent_strength_z"] is not None else -99))
for i,r in enumerate(teams,1):r["exposure_rank"]=i
# Pregame-frozen opponent exposure: do not use future-week ratings.
pregame_path=D/"pregame_opponent_exposure.csv"
assert pregame_path.exists(),"Pregame exposure export missing"
pregame=list(csv.DictReader(pregame_path.open()))
frozen_byteam=defaultdict(list);frozen_conference=defaultdict(list)
for row in pregame:
    t=canon(row["team"]);o=canon(row["opponent"])
    if t not in power or o not in power:continue
    strength=float(row["pregame_opponent_strength"])
    frozen_byteam[t].append(strength)
    if conf[t]==conf[o]:frozen_conference[t].append(strength)
for item in teams:
    t=item["team"];allvals=frozen_byteam[t];cv=frozen_conference[t]
    item["pregame_opponent_strength"]=round(average(allvals),5) if allvals else None
    item["pregame_conference_opponent_strength"]=round(average(cv),5) if cv else None
    item["pregame_exposure_games"]=len(allvals)
    item["pregame_conference_games"]=len(cv)
    item["pregame_exposure_z"]=round((average(allvals)-mu)/sd,4) if allvals else None
teams.sort(key=lambda x: -(x["pregame_exposure_z"] if x["pregame_exposure_z"] is not None else -99))
for i,item in enumerate(teams,1):item["pregame_exposure_rank"]=i
with (D/"pregame_exposure_summary.csv").open("w",newline="") as f:
    cols=["team","conference","pregame_opponent_strength","pregame_conference_opponent_strength",
          "pregame_exposure_games","pregame_conference_games","pregame_exposure_z","pregame_exposure_rank"]
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows({k:r[k] for k in cols} for r in teams)
(D/"conference_strength.json").write_text(json.dumps({"season":2026,"through_week":6,"method":"conference descriptive cross-sectional ratings, no production impact","note":"Opponent exposure uses end-of-week opponent strength; it is descriptive, not frozen pregame evidence. Nonconference residuals use end-of-week strengths and must not be used for pregame predictive inputs.","conferences":results,"teams":teams},indent=2))
for filename,items in [("conference_strength.csv",results),("conference_exposure.csv",teams)]:
    cols=list(items[0])
    with (D/filename).open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(items)
print("Conference rankings:",[(r["conference_rank"],r["conference"],r["conference_strength"]) for r in results])
