#!/usr/bin/env python3
"""Research-only empirical opponent-unit adjustment; preserves all prior outputs."""
import csv,json,statistics,math
from collections import defaultdict
from pathlib import Path
import test_betwise_dominance_market_baseline as base
import test_pure_units_expected_residual as b
D=Path("data/research/2026")
K=("PO","PD","RO","RD")
MATCH={"PO":"PD","PD":"PO","RO":"RD","RD":"RO"}
teams=base.teams
records=[]
for r in b.fbs:
    vals={k:(b.pure_rush_measure(r,k) if k in ("RO","RD") else b.pure_pass_measure(r,k)) for k in K}
    if any(v is None for v in vals.values()):continue
    records.append({"team":r["team"],"opponent":r["opponent"],"week":int(r["week"]),"game_id":r["game_id"],"plays":max(1,b.m.num(r.get("plays_count")) or 1.),"values":vals})
if len(records)<200:raise ValueError("Too few complete team-game records")
# Every team and unit is estimated separately from its FBS games.
by_team=defaultdict(list)
for x in records:by_team[x["team"]].append(x)
means={k:{t:(statistics.fmean(x["values"][k] for x in by_team[t]) if by_team[t] else 0.) for t in teams} for k in K}
z=lambda d:base.standardize(d)
unit_z={k:z(means[k]) for k in K}
# Estimate empirical beta against opposing matching-unit strength; within-team
# centering removes persistent team strength from the regression, reducing
# confounding. Opponent unit estimates exclude the SAME matchup where possible.
observations={k:[] for k in K}
for x in records:
    t,o=x["team"],x["opponent"]
    for k in K:
        other=MATCH[k]
        opposing=[y["values"][other] for y in by_team[o] if y["game_id"]!=x["game_id"]]
        if len(opposing)<2:continue
        opp_mean=statistics.fmean(opposing)
        overall=means[other]
        sd=statistics.pstdev(list(overall.values())) or 1.
        opp_z=(opp_mean-statistics.fmean(overall.values()))/sd
        response=x["values"][k]-means[k][t]
        observations[k].append((t,opp_z,response))
betas={}
audit_coeff={}
for k,obs in observations.items():
    # Remove within-team differences in average faced opponent strengths.
    opponent_avg={t:statistics.fmean(v for team,v,_ in obs if team==t) for t in set(a for a,_,_ in obs)}
    numer=sum((v-opponent_avg[t])*y for t,v,y in obs)
    denom=sum((v-opponent_avg[t])**2 for t,v,y in obs)
    slope=numer/denom if denom else 0.
    # A stronger opposing unit should normally suppress measured performance.
    # Bound unstable signs to zero rather than force a positive bonus.
    betas[k]=max(0.,min(1.5,-slope))
    audit_coeff[k]={"estimated_slope":round(slope,6),"adjustment_beta":round(betas[k],6),"team_games":len(obs),"unit_compared":MATCH[k]}
adjusted=defaultdict(lambda:defaultdict(list))
ledger=[]
for x in records:
    t,o=x["team"],x["opponent"]
    for k in K:
        opposing=[y["values"][MATCH[k]] for y in by_team[o] if y["game_id"]!=x["game_id"]]
        opp=statistics.fmean(opposing) if len(opposing)>=2 else means[MATCH[k]][o]
        full=means[MATCH[k]]
        opp_z=(opp-statistics.fmean(full.values()))/(statistics.pstdev(list(full.values())) or 1.)
        actual=x["values"][k]
        adjust=betas[k]*opp_z
        value=actual+adjust
        adjusted[t][k].append((value,x["plays"]))
        ledger.append({"team":t,"opponent":o,"week":x["week"],"game_id":x["game_id"],"unit":k,"opposing_unit":MATCH[k],"observed":round(actual,5),"opponent_unit_z":round(opp_z,5),"beta":round(betas[k],5),"adjustment":round(adjust,5),"adjusted":round(value,5)})
def wmean(pairs):
    return sum(v*w for v,w in pairs)/sum(w for _,w in pairs) if pairs else 0.
unit_team={t:{k:wmean(adjusted[t][k]) for k in K} for t in teams}
unit_component=base.standardize({t:statistics.fmean(unit_team[t].values()) for t in teams})
weights={"four_unit":.25,"earned_competition":.35,"market_strength_ats":.25,"results":.15}
new=[]
for t in teams:
    components={"four_unit":unit_component[t],"earned_competition":base.competition[t],"market_strength_ats":base.market_strength_with_residual[t],"results":base.results[t]}
    score=sum(weights[k]*v for k,v in components.items())
    new.append({"team":t,"score_z":round(score,5),"dominance_index":round(50+15*score,2),**{k:round(v,4) for k,v in components.items()},**{k:round(unit_team[t][k],5) for k in K}})
new.sort(key=lambda x:(-x["score_z"],x["team"]))
for i,x in enumerate(new,1):x["rank"]=i
old=base.variants["25_35_25_15"]
old_by={r["team"]:r for r in old}
for x in new:x["previous_rank"]=old_by[x["team"]]["rank"]
out={"description":"Empirically fitted unit-matched opponent adjustment vs previous overall-strength beta=0.50; retrospective descriptive research","weights":weights,"coefficients":audit_coeff,"sample_team_games":len(records),"caveats":["Adjusted matched-unit values and fit use season-to-date data, not guaranteed frozen pregame units.","Coefficients fit within-team regression on opponent unit; cannot establish causation.","No prior output was overwritten.","Market, competition and results scores unchanged."],"previous":old,"new_unit_adjustment":new}
(D/"betwise_unit_matched_comparison.json").write_text(json.dumps(out,indent=2))
with (D/"betwise_unit_matched_comparison.csv").open("w",newline="") as f:
    w=csv.writer(f);w.writerow(["rank","team","dominance_index","previous_rank","PO","PD","RO","RD","four_unit","earned_competition","market_strength_ats","results"])
    for x in new:w.writerow([x.get(k) for k in ["rank","team","dominance_index","previous_rank","PO","PD","RO","RD","four_unit","earned_competition","market_strength_ats","results"]])
with (D/"betwise_unit_matched_game_ledger.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(ledger[0]));w.writeheader();w.writerows(ledger)
print("Unit betas:",audit_coeff)
print("NEW TOP25",[(x["rank"],x["team"],x["previous_rank"]) for x in new[:25]])
