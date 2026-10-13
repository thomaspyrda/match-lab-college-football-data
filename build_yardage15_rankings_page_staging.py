#!/usr/bin/env python3
"""Research-only display feed for CFB Strength/Offense/Defense pages.
Uses approved 2026 yardage-inclusive overall score and unit ratings.
Opponent quality uses pregame prior-week opponent combined offense/defense ratings;
Week 1 and missing snapshots excluded; no future-week lookahead.
"""
import csv,json,statistics
from collections import defaultdict
from pathlib import Path
D=Path("data/research/2026")
overall=json.loads((D/"betwise_yardage15_overall_comparison.json").read_text())
week=overall["through_week"];teams={r["team"]:r for r in overall["rows"]}
units=list(csv.DictReader((D/"opponent_unit_yardage15_suppression_weekly_comparison.csv").open()))
snap=defaultdict(dict)
for r in units:
 if float(r["max_suppression"])==1.:
  snap[int(r["through_week"]),r["team"]][r["unit"]]=float(r["rating"])
# Rank offense/defense by combined unit z (not summed ratings with unrelated baselines).
latest={t:snap[week,t] for t in teams}
def combo(t,k1,k2):return statistics.fmean(latest[t][k] for k in (k1,k2))
offorder=sorted(teams,key=lambda t:(-combo(t,"PO","RO"),t))
deforder=sorted(teams,key=lambda t:(-combo(t,"PD","RD"),t))
offrank={t:i+1 for i,t in enumerate(offorder)}
defrank={t:i+1 for i,t in enumerate(deforder)}
played=defaultdict(list);wins=defaultdict(int);losses=defaultdict(int)
for g in csv.DictReader((D/"games.csv").open()):
 w=int(g["week"])
 if w>week:continue
 h,a=g["home"],g["away"]
 if h not in teams or a not in teams:continue
 hs,ass=int(g["home_points"]),int(g["away_points"])
 if hs>ass:wins[h]+=1;losses[a]+=1
 elif ass>hs:wins[a]+=1;losses[h]+=1
 for team,opp in ((h,a),(a,h)):
  # previous week's opponent unit quality only, not a current retrospective estimate
  previous=snap.get((w-1,opp))
  if not previous or len(previous)!=4:continue
  played[team].append({"week":w,"opponent":opp,"opponent_offense":round(statistics.fmean(previous[k] for k in ("PO","RO")),3),"opponent_defense":round(statistics.fmean(previous[k] for k in ("PD","RD")),3)})
rows=[]
for t in teams:
 r=teams[t];opps=played[t]
 row={"team":t,"team_strength_rank":r["rank"],"team_strength":r["rating"],"offensive_strength_rank":offrank[t],"offensive_strength":round(combo(t,"PO","RO"),3),"defensive_strength_rank":defrank[t],"defensive_strength":round(combo(t,"PD","RD"),3),"passing_offense":round(latest[t]["PO"],3),"rushing_offense":round(latest[t]["RO"],3),"passing_defense":round(latest[t]["PD"],3),"rushing_defense":round(latest[t]["RD"],3),"average_defense_faced":round(statistics.fmean(x["opponent_defense"] for x in opps),3) if opps else None,"average_offense_faced":round(statistics.fmean(x["opponent_offense"] for x in opps),3) if opps else None,"opponent_quality_games":len(opps),"fbs_record_from_game_archive":f"{wins[t]}-{losses[t]}","ap_rank":None,"sos_rank":None}
 rows.append(row)
assert len(rows)==136
assert sorted(x["team_strength_rank"] for x in rows)==list(range(1,137))
assert sorted(x["offensive_strength_rank"] for x in rows)==list(range(1,137))
assert sorted(x["defensive_strength_rank"] for x in rows)==list(range(1,137))
out={"season":2026,"through_week":week,"status":"research display staging—not live","notes":["AP, SOS and overall record MUST be joined from existing authoritative production sources, not assigned invented values. Null fields in staging must not overwrite live AP/SOS fields.","FBS archive record excludes FCS opponents and is not a substitute for overall team record.","Average opposing offensive/defensive quality uses opponent ratings frozen at the end of the previous week, excludes Week 1 and other unavailable opponents; per-game equal weighting.","Offense/Defense combination uses arithmetic mean of the two unit rating metrics; rank ordered descending.","Overall Team Strength is the independently approved 25/35/25/15 rating and is preserved."],"teams":rows}
(D/"yardage15_rankings_page_staging.json").write_text(json.dumps(out,indent=2))
with (D/"yardage15_rankings_page_staging.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print("Staged",len(rows),"teams; sample",rows[:3],flush=True)
