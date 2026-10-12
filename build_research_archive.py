#!/usr/bin/env python3
"""Archive reproducible 2026 game-level 41 x 2 FBS metrics; never modify production."""
import ast,csv,json,os,time,urllib.request,urllib.parse,statistics
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parent; SEASON=int(os.getenv("RESEARCH_SEASON","2026"))
OUT=ROOT/"data"/"research"/str(SEASON); OUT.mkdir(parents=True,exist_ok=True)
KEY=os.environ.get("CFBD_API_KEY")
if not KEY: raise SystemExit("Missing CFBD_API_KEY")
def api(route,**params):
    url="https://api.collegefootballdata.com"+route+"?"+urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)
        except Exception:
            if attempt==4:raise
            time.sleep(2**attempt)
def canon(x):
    return {"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}.get(x,x)
# Extract metric definitions and functions directly from version-controlled v15:
# one source of truth, rather than maintaining a drifting second 41-metric schema.
tree=ast.parse((ROOT/"experiment_dominance_v15.py").read_text())
wanted_functions={"f","mean","rate","situational_metrics","metric_row"}
selected=[]
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {"CATS","METRICS"} for t in node.targets):selected.append(node)
    if isinstance(node,ast.FunctionDef) and node.name in wanted_functions:selected.append(node)
ns={"statistics":statistics,"defaultdict":defaultdict}
exec(compile(ast.Module(body=selected,type_ignores=[]),"<v15 metric extraction>","exec"),ns)
metrics=ns["METRICS"];assert len(metrics)==41,f"Expected 41 metrics; got {len(metrics)}"
f=ns["f"]; metric_row=ns["metric_row"]; situational_metrics=ns["situational_metrics"]
FBS={canon(x["school"]) for x in api("/teams/fbs",year=SEASON) if x.get("school")}-{"Sacramento State","North Dakota State"}
# Prefer the existing validated production history; CFBD may vary field casing.
history_path=ROOT/"data"/"historical"/f"{SEASON}.json"
history=json.loads(history_path.read_text()).get("games",[]) if history_path.exists() else []
completed=[]
for g in history:
    result=g.get("result") or {}
    hp=result.get("home_points"); ap=result.get("away_points")
    if hp is None or ap is None:continue
    completed.append({"id":g.get("game_id"),"week":g.get("week"),
      "home_team":g.get("home"),"away_team":g.get("away"),
      "home_points":hp,"away_points":ap})
if not completed:
    games=api("/games",year=SEASON,seasonType="regular")
    for g in games:
        hp=g.get("home_points",g.get("homePoints"));ap=g.get("away_points",g.get("awayPoints"))
        if hp is None or ap is None:continue
        completed.append({"id":g.get("id",g.get("gameId")),"week":g.get("week"),
          "home_team":g.get("home_team",g.get("homeTeam")),
          "away_team":g.get("away_team",g.get("awayTeam")),
          "home_points":hp,"away_points":ap})
print("ARCHIVE INPUT:",json.dumps({"history_games":len(history),"completed":len(completed)}),flush=True)
if not completed:raise SystemExit("No completed game results found")
completed.sort(key=lambda g:(int(g.get("week") or 0),str(g.get("id"))))
adv=api("/stats/game/advanced",year=SEASON,seasonType="regular",excludeGarbageTime="true")
by_gid=defaultdict(dict)
for r in adv:
    if r.get("gameId") is not None and r.get("team"):by_gid[str(r["gameId"])][canon(r["team"])]=r
weekplays=defaultdict(lambda:defaultdict(list))
for week in sorted({int(g.get("week") or 0) for g in completed}):
    for p in api("/plays",year=SEASON,week=week,seasonType="regular"):
        if p.get("gameId") is not None and p.get("offense"):
            weekplays[str(p["gameId"])][canon(p["offense"])].append(p)
columns=["season","week","game_id","team","opponent","location","team_points","opponent_points","win","fbs_opponent","plays_count"]+["off_"+m for m in metrics]+["def_"+m for m in metrics]
records=[];ledger=[];missing=[]
for g in completed:
    gid=str(g["id"]);home=canon(g["home_team"]);away=canon(g["away_team"])
    if not(home in FBS or away in FBS):continue
    ap=by_gid.get(gid,{})
    ledger.append({"season":SEASON,"week":g.get("week"),"game_id":gid,"home":home,"away":away,"home_points":g["home_points"],"away_points":g["away_points"]})
    for team,opp,loc,tp,op in [(home,away,"H",g["home_points"],g["away_points"]),(away,home,"A",g["away_points"],g["home_points"])]:
        if team not in FBS:continue
        own=ap.get(team);enemy=ap.get(opp)
        if not own or not enemy:
            missing.append({"game_id":gid,"team":team,"missing":"advanced_game_row"});continue
        ownplays=weekplays[gid].get(team,[])
        oppplays=weekplays[gid].get(opp,[])
        off=metric_row(own,tp,situational_metrics(ownplays))
        deff=metric_row(enemy,op,situational_metrics(oppplays))
        row={"season":SEASON,"week":g["week"],"game_id":gid,"team":team,"opponent":opp,"location":loc,"team_points":tp,"opponent_points":op,"win":int(tp>op),"fbs_opponent":int(opp in FBS),"plays_count":len(ownplays)}
        row.update({"off_"+m:off.get(m) for m in metrics})
        row.update({"def_"+m:deff.get(m) for m in metrics})
        records.append(row)
with (OUT/"weekly_team_metrics.csv").open("w",newline="") as stream:
    w=csv.DictWriter(stream,fieldnames=columns);w.writeheader();w.writerows(records)
with (OUT/"games.csv").open("w",newline="") as stream:
    w=csv.DictWriter(stream,fieldnames=["season","week","game_id","home","away","home_points","away_points"]);w.writeheader();w.writerows(ledger)
(OUT/"preseason_anchors.json").write_text((ROOT/"data"/"preseason"/f"{SEASON}.json").read_text())
(OUT/"metric_dictionary.json").write_text(json.dumps({"categories":ns["CATS"],"metric_names":metrics,"columns":columns},indent=2))
coverage={m:sum(r.get("off_"+m) is not None for r in records) for m in metrics}
report={"season":SEASON,"completed_games":len(ledger),"team_game_rows":len(records),"fbs_teams":len(FBS),"metrics_per_side":41,"metric_coverage_counts":coverage,"missing_advanced_rows":missing}
(OUT/"coverage.json").write_text(json.dumps(report,indent=2))
if not records:
    print("MATCH DIAGNOSTIC:",json.dumps({"completed":len(completed),"fbs_count":len(FBS),
      "adv_rows":len(adv),"adv_games":len(by_gid),"first_adv_keys":list(adv[0]) if adv else [],
      "first_missing":missing[:3],"first_fbs":sorted(FBS)[:5]}),flush=True)
assert len(records)>0,"No complete usable team/game rows"
print(json.dumps({k:v for k,v in report.items() if k not in ("metric_coverage_counts","missing_advanced_rows")}))
