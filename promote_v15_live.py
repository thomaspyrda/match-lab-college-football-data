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
def score(rank,n):
    if rank is None or n<2:return None
    return round(100-99*(rank-1)/(n-1),1)
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
for r in cur["teams"]:
    x=rows.get(canon(r["team"]))
    if not x: continue
    r["national_strength_rank"]=x["rank"]
    r["strength_score"]=score(x["rank"],n); r["strength_tier"]=tier(r["strength_score"]); r["top_percent"]=round(101-r["strength_score"],1)
    r["overall_strength_rank"]=x["rank"]; r["overall_strength_score"]=r["strength_score"]; r["overall_strength_tier"]=r["strength_tier"]
    r["offensive_strength_rank"]=x["offense_rank"]; r["offensive_strength"]=score(x["offense_rank"],n); r["offensive_strength_tier"]=tier(r["offensive_strength"])
    r["defensive_strength_rank"]=x["defense_rank"]; r["defensive_strength"]=score(x["defense_rank"],n); r["defensive_strength_tier"]=tier(r["defensive_strength"])
    r["team_strength_sd"]=x["overall_team_strength_sd"]; r["offensive_strength_sd"]=x["offense_strength_sd"]; r["defensive_strength_sd"]=x["defense_strength_sd"]
    r["games_modeled"]=x["games"]; r["preseason_weight"]=x["preseason_weight"]; r["unit_strength_model"]="validated_v15_recursive_dominance"
cur["teams"].sort(key=lambda r:(r.get("overall_strength_rank") or 999,r["team"]))
cur["fbs_field_size"]=n
cur["model"]={
 "version":"v15",
 "status":"production_frozen",
 "overall":"50% Offensive Strength + 50% Defensive Strength.",
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
        p=g[side]; p["national_strength_rank"]=x["rank"]; p["strength_score"]=score(x["rank"],n); p["strength_tier"]=tier(p["strength_score"]); p["top_percent"]=round(101-p["strength_score"],1)
        p["team_strength_sd"]=x["overall_team_strength_sd"]; p["strength_source"]="validated_v15_recursive_dominance"
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
        p=g[side]; p["national_strength_rank"]=x["rank"]; p["strength_score"]=score(x["rank"],nn); p["strength_tier"]=tier(p["strength_score"]); p["top_percent"]=round(101-p["strength_score"],1)
        p["team_strength_sd"]=x["overall_team_strength_sd"]; p["strength_source"]="validated_v15_recursive_dominance"
hp.write_text(json.dumps(hist,separators=(",",":"))+"\n")
print(f"Promoted validated v15 Week {week}: {n} FBS teams; current rankings, upcoming profiles, and 2026 Weeks 2-6 historical profiles updated.")
