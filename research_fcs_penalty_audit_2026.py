#!/usr/bin/env python3
"""Read-only completed 2026 FBS vs FCS penalty audit."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent
hist=json.loads((root/"data/historical/2026.json").read_text())["games"]
data=json.loads((root/"data/current_rankings.json").read_text())
aliases={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
canon=lambda t:aliases.get(t,t)
fbs={canon(r["team"]) for r in data["teams"]}
through=int(data["through_week"])
tiers={"win_7_to_10":[],"win_1_to_6":[],"loss_1_to_10":[],"loss_11_plus":[]}
review=[]
for g in hist:
 week=int(g.get("week") or 0);result=g.get("result") or {}
 if not 1<=week<=through:continue
 h,a=canon(g.get("home","")),canon(g.get("away",""))
 if (h in fbs)==(a in fbs):continue
 try:hp=int(result["home_points"]);ap=int(result["away_points"])
 except (TypeError,ValueError,KeyError):continue
 t=h if h in fbs else a;opp=a if h in fbs else h
 margin=hp-ap if h in fbs else ap-hp
 entry={"week":week,"team":t,"fcs":opp,"margin":margin,"score":f"{hp}-{ap}"}
 review.append(entry)
 key="win_7_to_10" if 7<=margin<=10 else "win_1_to_6" if 1<=margin<=6 else "loss_1_to_10" if -10<=margin<=-1 else "loss_11_plus" if margin<=-11 else None
 if key:tiers[key].append(entry)
print("FCS_AUDIT|through_week",through,"|fbs_fcs_completed",len(review),"|qualifying_games",sum(map(len,tiers.values())))
for k,items in tiers.items():
 print("TIER",k,"GAMES",len(items),"UNIQUE_TEAMS",len({x["team"] for x in items}))
 for x in sorted(items,key=lambda x:(x["team"],x["week"])):print("CASE",k,x["team"],"vs",x["fcs"],"week",x["week"],"score",x["score"],"FBS_margin",x["margin"])
print("TOTAL_UNIQUE_TEAMS",len({x["team"] for v in tiers.values() for x in v}))
