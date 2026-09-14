#!/usr/bin/env python3
import csv,json
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"data"; (OUT/"weekly").mkdir(parents=True,exist_ok=True); (OUT/"games").mkdir(parents=True,exist_ok=True)
def rows(name):
 with (ROOT/name).open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def n(v): return int(v) if v not in ("",None) else None
weekly=rows("match_lab_ap_elo_master.csv"); games=rows("match_lab_game_ap_elo.csv")
years=sorted({int(r["season"]) for r in weekly})
manifest={"schema_version":"1.0","updated":"2026-09-14","seasons":[]}
for year in years:
 yr=[r for r in weekly if int(r["season"])==year]; weeks={}
 for r in yr:
  w=str(int(r["effective_week"])); leaf=weeks.setdefault(w,{"teams":{}})
  leaf["teams"][r["team"]]={"ap_rank":n(r["ap_rank"]),"national_strength_rank":n(r["elo_rank"]),"fbs_field_size":n(r["fbs_field_size"]),"strength_score":n(r["strength_score"]),"strength_tier":r["strength_tier"] or None,"top_percent":n(r["top_percent"]),"available":r["strength_score"]!=""}
 for w in weeks:
  weeks[w]["ranking"]=sorted(weeks[w]["teams"],key=lambda t:(weeks[w]["teams"][t]["national_strength_rank"] is None,weeks[w]["teams"][t]["national_strength_rank"] or 999,t))
 (OUT/"weekly"/f"{year}.json").write_text(json.dumps({"season":year,"weeks":weeks},separators=(",",":")),encoding="utf-8")
 gy=[r for r in games if int(r["season"])==year]; grouped={}
 for r in gy:
  g=grouped.setdefault(str(r["game_id"]),{"game_id":str(r["game_id"]),"week":int(r["week"]),"start_date":r["start_date"],"teams":{}})
  g["teams"][r["team"]]={"side":r["side"],"opponent":r["opponent"],"ap_rank":n(r["ap_rank"]),"national_strength_rank":n(r["pregame_elo_rank"]),"fbs_field_size":n(r["fbs_field_size"]),"strength_score":n(r["strength_score"]),"strength_tier":r["strength_tier"] or None,"top_percent":n(r["top_percent"])}
 (OUT/"games"/f"{year}.json").write_text(json.dumps({"season":year,"games":grouped},separators=(",",":")),encoding="utf-8")
 manifest["seasons"].append({"season":year,"weeks":sorted(map(int,weeks)),"weekly_url":f"data/weekly/{year}.json","games_url":f"data/games/{year}.json","team_week_rows":len(yr),"game_team_rows":len(gy)})
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("Built web data:",", ".join(map(str,years)))
