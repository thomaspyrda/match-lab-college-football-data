#!/usr/bin/env python3
"""Isolated strict opponent-quality cutoff experiment. Never alters preserved v1."""
import csv,json,statistics
from collections import defaultdict
from pathlib import Path
import test_betwise_2025_coefficients_on_2026 as prior
D=Path("data/research/2026");base=prior.current.base;teams=prior.current.teams
# Independent, no-preseason market-spread ordering; #51+ are INELIGIBLE.
market_rank={r["team"]:r["rank"] for r in json.loads((D/"market_no_preseason_comparison.json").read_text())["variants"]["market_only"]}
assert len(market_rank)==len(teams)
def eligible(rank):return max(0.,(51-rank)/50.)*1.5 if rank<=50 else 0.
def standardize(values):return base.standardize(values)
unit_values=defaultdict(lambda:defaultdict(list))
events=defaultdict(list)
audit=[]
for x in prior.current.records:
 t=x["team"];opp=x["opponent"];rank=market_rank[opp]
 for k in prior.current.K:
  target=prior.current.MATCH[k]
  peers=[z["values"][target] for z in prior.current.by_team[opp] if z["game_id"]!=x["game_id"]]
  opposing=statistics.fmean(peers) if len(peers)>=2 else prior.current.means[target][opp]
  full=prior.current.means[target]
  oz=(opposing-statistics.fmean(full.values()))/(statistics.pstdev(list(full.values())) or 1.)
  adjusted=x["values"][k]+prior.old_betas[k]*oz
  capped=min(0.,adjusted) if rank>50 else adjusted
  unit_values[t][k].append((capped,x["plays"]))
  audit.append({"team":t,"opponent":opp,"market_rank":rank,"week":x["week"],"unit":k,"raw_adjusted":round(adjusted,5),"after_cutoff":round(capped,5)})
# Keep the exact fixed historical betas and original unit measurement; only cap
# positive measurements obtained against #51+ opponents.
unit_team={t:{k:prior.current.wmean(unit_values[t][k]) for k in prior.current.K} for t in teams}
unit_component=standardize({t:statistics.fmean(unit_team[t].values()) for t in teams})
competition_events=defaultdict(list);results_events=defaultdict(list);ats_events=defaultdict(list)
for g in base.games:
 h,a=g["home"],g["away"]
 if h not in market_rank or a not in market_rank:continue
 margin=float(g["actual_home_margin"]);ats=float(g["ats_home"])
 for t,o,m,resid in [(h,a,margin,ats),(a,h,-margin,-ats)]:
  rank=market_rank[o];qual=eligible(rank);win=m>0
  # Zero positive competition credit for #51+; losses retain penalties, worse vs weak.
  c=qual if win else -(0.7+0.8*(rank-1)/135.)
  result=qual/1.5 if win else -(1.+0.5*(rank-1)/135.)
  competition_events[t].append(c);results_events[t].append(result)
  # Keep absolute market baseline; prevent weak opposition yielding positive ATS residual.
  weight=max(.65,min(1.5,1+.25*base.market_z[o]))
  ats_events[t].append((min(0.,resid) if rank>50 else resid,weight))
competition=standardize({t:statistics.fmean(competition_events[t]) if competition_events[t] else 0. for t in teams})
results=standardize({t:statistics.fmean(results_events[t]) if results_events[t] else 0. for t in teams})
market=standardize({t:base.market_power[t]+.5*(sum(v*w for v,w in ats_events[t])/(sum(w for _,w in ats_events[t])+3) if ats_events[t] else 0.) for t in teams})
rows=[]
for t in teams:
 s=.25*unit_component[t]+.35*competition[t]+.25*market[t]+.15*results[t]
 rows.append({"team":t,"score_z":round(s,6),"dominance_index":round(50+15*s,2),"four_unit":round(unit_component[t],5),"earned_competition":round(competition[t],5),"market_strength_ats":round(market[t],5),"results":round(results[t],5)})
rows.sort(key=lambda r:(-r["score_z"],r["team"]))
baseline={r["team"]:r for r in prior.rows}
for i,r in enumerate(rows,1):
 r["rank"]=i;r["previous_rank"]=baseline[r["team"]]["rank"];r["rank_change"]=r["previous_rank"]-i;r["market_rank"]=market_rank[r["team"]]
assert len(rows)==136
out={"label":"EXPERIMENT ONLY: strict #50 opponent-quality cutoff","formula":"25/35/25/15 with frozen 2025 fitted matched-unit betas","rank_reference":"2026 no-preseason market-only full-period strength ranks (not recursive BetWise rank)","cutoff":"Opponent rank >50 earns ZERO positive competition credit, results win credit, ATS residual, and adjusted unit game-value. Negative values retained.","competition_win_curve":"For opponent rank 1..50: 1.5*(51-rank)/50; rank>50: 0","loss_penalty":"Competition -(0.7+0.8*(rank-1)/135); results -(1+0.5*(rank-1)/135)","notes":["2026 independent market ranks reflect all available 2026 lines, not strictly pregame-safe ranks.","Z-standardization can shift relative values, but no weak-opponent event contributes a positive raw reward.","Market baseline retained because it measures absolute team strength, not a per-game weak-opponent bonus.","Both components containing wins are opponent quality adjusted; some overlap remains.","Frozen 2025 coefficients and 25/35/25/15 preserved. Production untouched."],"rows":rows,"baseline":prior.rows,"coefficients":prior.old_betas}
(D/"betwise_strict_rank50_cutoff_comparison.json").write_text(json.dumps(out,indent=2))
with (D/"betwise_strict_rank50_cutoff_comparison.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (D/"betwise_strict_rank50_game_audit.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
print("Strict50 Top30",[(r["rank"],r["team"],r["previous_rank"]) for r in rows[:30]])
