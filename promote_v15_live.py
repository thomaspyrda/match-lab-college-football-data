#!/usr/bin/env python3
"""Promote the frozen validated v15 Team Strength model to current live data."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data"; EXP=DATA/"experiments"
ALIASES={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
def canon(x): return ALIASES.get(x,x)
def tier(s):
    if s is None:return None
    if s>=95:return "Elite"
    if s>=85:return "Great"
    if s>=76:return "Very Strong"
    if s>=65:return "Strong"
    if s>=50:return "Above Average"
    return "Below Average"
def score_from_sd(sd):
    """Convert standardized strength to a 1-100 performance rating.

    Rank and rating are intentionally separate: #1 does not automatically equal 100.
    The upper tail is compressed so 95+ is rare and 100 requires an extreme ~3.5 SD season.
    """
    if sd is None:return None
    anchors=[
        (-3.0,1),(-2.5,3),(-2.0,6),(-1.5,15),(-1.0,25),(-0.5,35),
        (0.0,50),(0.5,65),(1.0,75),(1.5,85),(2.0,94),(2.5,97),(3.0,99),(3.5,100)
    ]
    x=float(sd)
    if x<=anchors[0][0]:return 1.0
    if x>=anchors[-1][0]:return 100.0
    for (x0,y0),(x1,y1) in zip(anchors,anchors[1:]):
        if x0<=x<=x1:
            return round(y0+(y1-y0)*(x-x0)/(x1-x0),1)
    return None

def top_percent(rank,n):
    if rank is None or n<1:return None
    return round(100*rank/n,1)
def load_week(w):
    p=EXP/f"recursive_unit_strength_v15_2026_week_{w}.json"
    if not p.exists(): return None
    d=json.loads(p.read_text())
    assert d["schema_version"]=="experimental-15.0" and d["public_ui"] is False
    return d
cur=json.loads((DATA/"current_rankings.json").read_text())
week=int(cur["week"]); v=load_week(week)
if not v: raise SystemExit(f"Missing validated v15 Week {week} output")
rows={canon(r["team"]):r for r in v["rankings"]}; n=len(rows)
assert n>=130
cur["teams"]=[r for r in cur["teams"] if canon(r["team"]) in rows]
for r in cur["teams"]:
    x=rows[canon(r["team"])]
    r["national_strength_rank"]=x["rank"]
    r["team_strength_sd"]=x["overall_team_strength_sd"]; r["offensive_strength_sd"]=x["offensive_strength_sd"]; r["defensive_strength_sd"]=x["defensive_strength_sd"]
    r["strength_score"]=score_from_sd(r["team_strength_sd"]); r["strength_tier"]=tier(r["strength_score"]); r["top_percent"]=top_percent(x["rank"],n)
    r["overall_strength_rank"]=x["rank"]; r["overall_strength_score"]=r["strength_score"]; r["overall_strength_tier"]=r["strength_tier"]
    r["offensive_strength_rank"]=x["offense_rank"]; r["offensive_strength"]=score_from_sd(r["offensive_strength_sd"]); r["offensive_strength_tier"]=tier(r["offensive_strength"])
    r["defensive_strength_rank"]=x["defense_rank"]; r["defensive_strength"]=score_from_sd(r["defensive_strength_sd"]); r["defensive_strength_tier"]=tier(r["defensive_strength"])
    r["games_modeled"]=x["games"]; r["preseason_weight"]=x["preseason_weight"]; r["unit_strength_model"]="validated_v15_recursive_dominance"
    # Dashboard-only situational unit ratings. These are already produced by the
    # frozen V15 solve; exposing them does not alter Team Strength or rankings.
    diag=x.get("diagnostics") or {}; offm=diag.get("offense_metrics") or {}; defm=diag.get("defense_metrics") or {}
    r["dashboard_situational"]={
      "third_down_conversion":offm.get("third_down_conversion"),
      "defensive_third_down_conversion":defm.get("third_down_conversion"),
      "red_zone_td_rate":offm.get("red_zone_td_rate"),
      "defensive_red_zone_td_rate":defm.get("red_zone_td_rate"),
      "red_zone_points_per_trip":offm.get("red_zone_points_per_trip"),
      "defensive_red_zone_points_per_trip":defm.get("red_zone_points_per_trip"),
    }
cur["teams"].sort(key=lambda r:(r.get("overall_strength_rank") or 999,r["team"]))
cur["fbs_field_size"]=n
cur["model"]={
 "version":"v15",
 "status":"production_frozen",
 "overall":"50% Offensive Strength + 50% Defensive Strength.",
 "display_rating":"1-100 ratings are calibrated from standard deviations above/below the FBS field; rank does not determine the rating. 95+ is intentionally rare and 100 requires approximately +3.5 SD.",
 "categories":"Scoring 22%, Efficiency 23%, Passing 18%, Rushing 17%, Line 10%, Finishing 10%.",
 "opponent_adjustment":"Each game metric is standardized against the FBS field and recursively adjusted for the corresponding opponent unit strength.",
 "preseason_prior":"Evidence-based decay: 100%, 75%, 55%, 40%, 20%, 5%, then 0% after six qualifying FBS games.",
 "fcs":"FCS games can penalize underperformance but do not create artificial positive strength credit.",
 "ap_rank":"reference only; never enters the formula",
 "metric_count":len(v["convergence"]),
}
(DATA/"current_rankings.json").write_text(json.dumps(cur,indent=2)+"\n")
# Overlay upcoming game profiles with the same live v15 board.
up=json.loads((DATA/"upcoming.json").read_text())
for g in up["games"]:
    for side,name in (("home_profile",g["home"]),("away_profile",g["away"])):
        x=rows.get(canon(name))
        if not x: continue
        p=g[side]; p["national_strength_rank"]=x["rank"]; p["team_strength_sd"]=x["overall_team_strength_sd"]; p["strength_score"]=score_from_sd(p["team_strength_sd"]); p["strength_tier"]=tier(p["strength_score"]); p["top_percent"]=top_percent(x["rank"],n)
        p["strength_source"]="validated_v15_recursive_dominance"
(DATA/"upcoming.json").write_text(json.dumps(up,indent=2)+"\n")
# Overlay 2026 historical pregame profiles wherever a validated v15 weekly snapshot exists.
hp=DATA/"historical"/"2026.json"; hist=json.loads(hp.read_text())
cache={}
for g in hist["games"]:
    w=int(g.get("week") or 0)
    if w<2 or w>6: continue
    if w not in cache:
        wd=load_week(w)
        cache[w]={canon(r["team"]):r for r in wd["rankings"]} if wd else {}
    board=cache[w]; nn=len(board)
    for side,name in (("home_profile",g["home"]),("away_profile",g["away"])):
        x=board.get(canon(name))
        if not x: continue
        p=g[side]; p["national_strength_rank"]=x["rank"]; p["team_strength_sd"]=x["overall_team_strength_sd"]; p["strength_score"]=score_from_sd(p["team_strength_sd"]); p["strength_tier"]=tier(p["strength_score"]); p["top_percent"]=top_percent(x["rank"],nn)
        p["strength_source"]="validated_v15_recursive_dominance"
hp.write_text(json.dumps(hist,separators=(",",":"))+"\n")
print(f"Promoted validated v15 Week {week}: {n} FBS teams; current rankings, upcoming profiles, and 2026 Weeks 2-6 historical profiles updated.")