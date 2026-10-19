#!/usr/bin/env python3
"""Promote approved 15% margin, asymmetric SOS and FCS adjusted ratings."""
import json
from pathlib import Path
ALIASES={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
def canon(x):return ALIASES.get(x,x)
def tier(s):return "Elite" if s>=95 else "Great" if s>=85 else "Very Strong" if s>=76 else "Strong" if s>=65 else "Above Average" if s>=50 else "Below Average"
def top_percent(rank,n):return round(100*rank/n,1)
def score_from_sd(sd):
 anchors=[(-3.0,1),(-2.5,3),(-2.0,6),(-1.5,15),(-1.0,25),(-0.5,35),(0.0,50),(0.5,65),(1.0,75),(1.5,85),(2.0,94),(2.5,97),(3.0,99),(3.5,100)]
 if sd<=anchors[0][0]:return 1.0
 if sd>=anchors[-1][0]:return 100.0
 for (x0,y0),(x1,y1) in zip(anchors,anchors[1:]):
  if x0<=sd<=x1:return round(y0+(y1-y0)*(sd-x0)/(x1-x0),1)
 raise ValueError(sd)
ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data"
cur=json.loads((DATA/"current_rankings.json").read_text())
source=json.loads((DATA/"experiments"/f"approved_four_unit_{int(cur['season'])}.json").read_text())
assert source["through_week"]==cur["through_week"],"Experiment must match completed week"
rows={canon(x["team"]):x for x in source["teams"]}
assert len(rows)>=130
cur["teams"]=[r for r in cur["teams"] if canon(r["team"]) in rows]
assert len(cur["teams"])==len(rows), "Missing modeled FBS teams in current dataset"
for r in cur["teams"]:
 x=rows.get(canon(r["team"]))
 if x is None:continue
 r["national_strength_rank"]=x["overall_rank"]
 r["overall_strength_rank"]=x["overall_rank"]
 r["team_strength_sd"]=x["overall_z"]
 r["strength_score"]=score_from_sd(x["overall_z"])
 r["strength_tier"]=tier(r["strength_score"])
 r["overall_strength_score"]=r["strength_score"]
 r["overall_strength_tier"]=r["strength_tier"]
 r["top_percent"]=top_percent(x["overall_rank"],len(rows))
 r["offensive_strength_sd"]=x["offense_z"]
 r["defensive_strength_sd"]=x["defense_z"]
 r["offensive_strength_rank"]=x["offense_rank"]
 r["defensive_strength_rank"]=x["defense_rank"]
 r["offensive_strength"]=score_from_sd(x["offense_z"])
 r["defensive_strength"]=score_from_sd(x["defense_z"])
 r["offensive_strength_tier"]=tier(r["offensive_strength"])
 r["defensive_strength_tier"]=tier(r["defensive_strength"])
 for key,unit in (("passing_offense_strength","PO"),("rushing_offense_strength","RO"),("passing_defense_strength","PD"),("rushing_defense_strength","RD")):
  r[key]=score_from_sd(x["unit_z"][unit])
  r[key+"_rank"]=x["unit_ranks"][unit]
 r["games_modeled"]=x["games_evaluated"]
 r["quality_win_bonus_z"]=round(x["ap_bonus"],3)
 r["loss_penalty_z"]=round(-.20*x["losses"],3)
 r["sos_adjustment_z"]=round(x["sos_adjustment_z"],3)
 r["fcs_penalty_z"]=round(x["fcs_penalty_z"],3)
 r["preseason_anchor_weight"]=x["preseason_anchor_weight"]
 r["adjusted_scoring_margin_z"]=round(x["margin_z"],3)
 r["unit_strength_model"]=source["model"]
cur["teams"].sort(key=lambda r:(r.get("overall_strength_rank") or 999,r["team"]))
cur["fbs_field_size"]=len(rows)
cur["model"]={
 "version":source["model"],"status":"production_current",
 "overall":"85% opponent-adjusted four-unit strength + 15% uncapped opponent-adjusted scoring margin, cumulative AP-ranked win bonuses, asymmetric season SOS, -0.20 Z per loss, FCS underperformance penalties, and a decaying current-season preseason anchor through Week 6.",
 "unit_weights":"Equal PO RO PD RD; passing PPA/success/explosiveness 45/45/10, rushing 40/40/20.",
 "opponent_adjustment":"Chronological nonrecursive opponent unit strength frozen at pregame time.",
 "recent_form":"Last three completed games 1.25x, 1.50x, 2.00x.",
 "margin":"Uncapped opponent-adjusted scoring margin, 15% statistical performance.",
 "losses":"Each loss -0.20 Z, overall only.",
 "sos":"Asymmetric schedule strength, overall only.",
 "fcs":"Additional penalties for FCS wins by ten or fewer or FCS losses, overall only.",
 "preseason_anchor":"Week 1: 100%; Week 2: 75%; Week 3: 55%; Week 4: 40%; Week 5: 20%; Week 6: 5%; Week 7 onward: 0%. Current-season preseason consensus required.",
 "display_rating":"Standardized model mapped to 1-100 rating."
}
(DATA/"current_rankings.json").write_text(json.dumps(cur,indent=2)+"\n")
up_path=DATA/"upcoming.json"
if up_path.exists():
 up=json.loads(up_path.read_text())
 for g in up.get("games",[]):
  for side,team in (("home_profile",g.get("home")),("away_profile",g.get("away"))):
   x=rows.get(canon(team)) if team else None
   if x and side in g and isinstance(g[side],dict):
    p=g[side];p["national_strength_rank"]=x["overall_rank"];p["team_strength_sd"]=x["overall_z"];p["strength_score"]=score_from_sd(x["overall_z"]);p["strength_tier"]=tier(p["strength_score"]);p["strength_source"]=source["model"]
 up_path.write_text(json.dumps(up,indent=2)+"\n")
print("PROMOTED",len(rows),"TEAMS",source["model"],"through",source["through_week"])
