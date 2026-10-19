#!/usr/bin/env python3
"""Private, read-only strong SOS adjustment comparison; no production writes."""
import json,statistics
from pathlib import Path
root=Path(__file__).resolve().parent
exp=json.loads((root/"data/experiments/four_unit_chronological_10pct_margin_2026.json").read_text())
cur=json.loads((root/"data/current_rankings.json").read_text())
aliases={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
canon=lambda n:aliases.get(n,n)
data={canon(r["team"]):r for r in cur["teams"]}
rows=exp["teams"]; assert len(rows)==136
valid=[(r,data[canon(r["team"])]) for r in rows]
assert len(valid)==136 and all(a.get("schedule_strength") is not None for r,a in valid)
sos=[float(a["schedule_strength"]) for r,a in valid]
mu=statistics.fmean(sos); sd=statistics.pstdev(sos)
assert sd>0
original=sorted(valid,key=lambda pair:(-float(pair[0]["overall_z"]),pair[0]["team"]))
old_pos={canon(r["team"]):i for i,(r,a) in enumerate(original,1)}
adjusted=[]
for r,a in valid:
 team=canon(r["team"]);z=(float(a["schedule_strength"])-mu)/sd
 final=float(r["overall_z"])+.30*z
 adjusted.append({"team":team,"baseline":float(r["overall_z"]),"sos":float(a["schedule_strength"]),"sos_rank":a["schedule_strength_rank"],"sos_z":z,"sos_adj":.30*z,"overall":final})
adjusted.sort(key=lambda x:(-x["overall"],x["team"]))
print(f"STRONG_SOS_TEST through_week={exp['through_week']} teams={len(rows)} sos_mean={mu:.3f} sos_sd={sd:.3f}")
print("RANK|TEAM|NEW_Z|PRIOR_RANK|MOVE|BASE_Z|SOS_RANK|SOS_Z|SOS_ADJ")
for i,x in enumerate(adjusted,1):
 print(f"{i}|{x['team']}|{x['overall']:+.3f}|{old_pos[x['team']]}|{old_pos[x['team']]-i:+d}|{x['baseline']:+.3f}|{x['sos_rank']}|{x['sos_z']:+.3f}|{x['sos_adj']:+.3f}")
