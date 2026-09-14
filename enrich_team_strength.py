#!/usr/bin/env python3
import csv, json, hashlib
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FIELDS=("strength_score","strength_tier","top_percent")

def tier(score):
    return "Elite" if score>=90 else "Strong" if score>=75 else "Above Average" if score>=50 else "Below Average" if score>=25 else "Weak"

def strength(rating, values):
    if rating in (None,""): return {"strength_score":"","strength_tier":"","top_percent":""}
    x=int(rating); vals=[int(v) for v in values]
    below=sum(v<x for v in vals); tied=sum(v==x for v in vals)
    pct=100.0 if len(vals)<=1 else 100.0*(below+(max(tied,1)-1)/2)/(len(vals)-1)
    score=max(1,min(100,int(pct+0.5)))
    return {"strength_score":score,"strength_tier":tier(score),"top_percent":101-score}

def read_csv(name):
    with (ROOT/name).open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

def write_csv(name,rows,fields):
    with (ROOT/name).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

weekly=read_csv("match_lab_ap_elo_master.csv")
games=read_csv("match_lab_game_ap_elo.csv")
boards=defaultdict(list); weekly_team={}
for r in weekly:
    key=(r["season"],r["effective_week"]); weekly_team[key+(r["team"],)]=r
    if r["elo_rating"]!="": boards[key].append(int(r["elo_rating"]))
for r in weekly: r.update(strength(r["elo_rating"],boards[(r["season"],r["effective_week"])]))
for r in games:
    vals=list(boards[(r["season"],r["week"])])
    wr=weekly_team.get((r["season"],r["week"],r["team"]))
    if r["pregame_elo"]!="":
        if wr and wr["elo_rating"]!="":
            try: vals.remove(int(wr["elo_rating"]))
            except ValueError: pass
        vals.append(int(r["pregame_elo"]))
    r.update(strength(r["pregame_elo"],vals))

wf=list(weekly[0]); gi=wf.index("elo_rank")+1
for f in reversed(FIELDS):
    if f not in wf: wf.insert(gi,f)
gf=list(games[0]); gi=gf.index("pregame_elo_rank")+1
for f in reversed(FIELDS):
    if f not in gf: gf.insert(gi,f)
write_csv("match_lab_ap_elo_master.csv",weekly,wf)
write_csv("match_lab_game_ap_elo.csv",games,gf)

wl={"schema_version":"3.0","display_metric":"Team Strength","data":{}}
for r in weekly:
    leaf=wl["data"].setdefault(r["season"],{}).setdefault(r["effective_week"],{})
    leaf[r["team"]]={"ap_rank":int(r["ap_rank"]) if r["ap_rank"] else None,"elo_rating":int(r["elo_rating"]) if r["elo_rating"] else None,"elo_rank":int(r["elo_rank"]) if r["elo_rank"] else None,"strength_score":int(r["strength_score"]) if r["strength_score"]!="" else None,"strength_tier":r["strength_tier"] or None,"top_percent":int(r["top_percent"]) if r["top_percent"]!="" else None,"fbs_field_size":int(r["fbs_field_size"])}
gl={"schema_version":"3.0","display_metric":"Team Strength","data":{}}
for r in games:
    gl["data"].setdefault(r["game_id"],{})[r["team"]]={"ap_rank":int(r["ap_rank"]) if r["ap_rank"] else None,"pregame_elo":int(r["pregame_elo"]) if r["pregame_elo"] else None,"pregame_elo_rank":int(r["pregame_elo_rank"]) if r["pregame_elo_rank"] else None,"strength_score":int(r["strength_score"]) if r["strength_score"]!="" else None,"strength_tier":r["strength_tier"] or None,"top_percent":int(r["top_percent"]) if r["top_percent"]!="" else None,"fbs_field_size":int(r["fbs_field_size"])}
(ROOT/"match_lab_ap_elo_lookup.json").write_text(json.dumps(wl,separators=(",",":")),encoding="utf-8")
(ROOT/"match_lab_game_ap_elo_lookup.json").write_text(json.dumps(gl,separators=(",",":")),encoding="utf-8")

coverage=read_csv("match_lab_ap_elo_coverage.csv")
by_week=defaultdict(list)
for r in weekly: by_week[(r["season"],r["effective_week"])].append(r)
for r in coverage:
    rr=by_week[(r["season"],r["effective_week"])]
    r["strength_score_count"]=sum(x["strength_score"]!="" for x in rr)
    r["strength_score_status"]="PASS" if str(r["strength_score_count"])==r["elo_count"] else "FAIL"
cf=list(coverage[0])
for f in ("strength_score_count","strength_score_status"):
    if f not in cf: cf.append(f)
write_csv("match_lab_ap_elo_coverage.csv",coverage,cf)

assert len(weekly)==22246 and len(games)==17199
for r in weekly+games:
    if r["strength_score"]!="":
        s=int(r["strength_score"]); assert 1<=s<=100
        assert int(r["top_percent"])==101-s and r["strength_tier"]==tier(s)
assert all(r["strength_score_status"]=="PASS" for r in coverage)

files=["README.md","VALIDATION_REPORT.md","build_ap_elo.py","enrich_team_strength.py","hostinger_lookup.js","schema.sql","test_build.py","match_lab_ap_elo_master.csv","match_lab_game_ap_elo.csv","match_lab_ap_elo_coverage.csv","match_lab_ap_elo_lookup.json","match_lab_game_ap_elo_lookup.json"]
with (ROOT/"SHA256SUMS.txt").open("w",encoding="utf-8") as out:
    for name in files: out.write(f"{hashlib.sha256((ROOT/name).read_bytes()).hexdigest()}  {name}\n")
print(f"Validated {len(weekly):,} weekly and {len(games):,} game-team rows")
