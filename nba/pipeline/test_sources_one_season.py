#!/usr/bin/env python3
"""One-season source and consistency test; does not modify live team data."""
import json,time,traceback,sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
from nba_api.stats.endpoints import leaguegamelog,leaguedashteamstats
import requests
import build_teamrankings_games as betting

SEASON="2024-25"
YEAR=2025
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"nba/pipeline/source-test-results"/str(YEAR)
RAW=OUT/"raw"
RAW.mkdir(parents=True,exist_ok=True)
report={"season":SEASON,"started_at":datetime.now(timezone.utc).isoformat(),"sources":{},"checks":{},"live_data_changed":False}
datasets={}
def save():
    (OUT/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
def nba(name,factory):
    started=time.monotonic()
    try:
        obj=factory()
        rows=obj.get_data_frames()[0].to_dict("records")
        (RAW/(name+".json")).write_text(json.dumps(rows,default=str,allow_nan=False))
        datasets[name]=rows
        report["sources"][name]={"status":"downloaded","rows":len(rows),"seconds":round(time.monotonic()-started,1),"source":"https://stats.nba.com/stats/"+obj.endpoint}
    except Exception as exc:
        report["sources"][name]={"status":"failed","seconds":round(time.monotonic()-started,1),"error":str(exc)[:700]}
    save()
    print(name,json.dumps(report["sources"][name]),flush=True)
    time.sleep(2)

nba("team_games",lambda:leaguegamelog.LeagueGameLog(season=SEASON,season_type_all_star="Regular Season",player_or_team_abbreviation="T",timeout=25))
nba("team_base",lambda:leaguedashteamstats.LeagueDashTeamStats(season=SEASON,season_type_all_star="Regular Season",per_mode_detailed="Totals",measure_type_detailed_defense="Base",timeout=25))
nba("team_advanced",lambda:leaguedashteamstats.LeagueDashTeamStats(season=SEASON,season_type_all_star="Regular Season",per_mode_detailed="PerGame",measure_type_detailed_defense="Advanced",timeout=25))
nba("player_games",lambda:leaguegamelog.LeagueGameLog(season=SEASON,season_type_all_star="Regular Season",player_or_team_abbreviation="P",timeout=25))

def check(name,ok,details):
    report["checks"][name]={"passed":bool(ok),"details":details}
games=datasets.get("team_games",[])
base=datasets.get("team_base",[])
adv=datasets.get("team_advanced",[])
players=datasets.get("player_games",[])
bygame=defaultdict(list)
byteam=defaultdict(list)
for g in games:
    bygame[str(g["GAME_ID"])].append(g)
    byteam[int(g["TEAM_ID"])].append(g)
check("team_game_coverage",len(byteam)==30 and len(bygame)==1230 and len(games)==2460,{"teams":len(byteam),"games":len(bygame),"team_game_rows":len(games),"expected_games":1230})
paired=bool(games) and all(len(v)==2 and len({x["TEAM_ID"] for x in v})==2 and all(str(x["SEASON_ID"]).endswith("2024") for x in v) and all(x["WL"] in ("W","L") for x in v) and sum(x["WL"]=="W" for x in v)==1 for v in bygame.values())
check("paired_games_and_regular_season",paired,{"paired_games":sum(len(v)==2 for v in bygame.values())})
base_map={int(x["TEAM_ID"]):x for x in base}
mismatch=[]
for team,rows in byteam.items():
    b=base_map.get(team)
    if not b or len(rows)!=82 or int(b["GP"])!=len(rows) or int(b["W"])!=sum(x["WL"]=="W" for x in rows) or abs(float(b["PTS"])-sum(float(x["PTS"]) for x in rows))>.01:
        mismatch.append(team)
check("team_totals_match_game_logs",len(base_map)==30 and not mismatch and bool(games),{"team_rows":len(base_map),"mismatched_teams":mismatch})
needed=("OFF_RATING","DEF_RATING","NET_RATING","PACE","EFG_PCT","TS_PCT","TM_TOV_PCT","OREB_PCT")
missing={str(x["TEAM_ID"]):[k for k in needed if x.get(k) is None] for x in adv if any(x.get(k) is None for k in needed)}
check("official_advanced_metric_coverage",len(adv)==30 and not missing,{"team_rows":len(adv),"missing":missing,"columns":needed})
unique={(int(x["PLAYER_ID"]),int(x["TEAM_ID"]),str(x["GAME_ID"])) for x in players}
stints=defaultdict(list)
teams_per_player=defaultdict(set)
invalid_games=0
for p in players:
    tid=int(p["TEAM_ID"])
    pid=int(p["PLAYER_ID"])
    stints[(pid,tid)].append(p)
    teams_per_player[pid].add(tid)
    if str(p["GAME_ID"]) not in bygame or tid not in {int(g["TEAM_ID"]) for g in bygame[str(p["GAME_ID"])]}:invalid_games+=1
check("player_game_coverage",bool(players) and len({int(p["TEAM_ID"]) for p in players})==30 and len(unique)==len(players) and invalid_games==0,{"rows":len(players),"teams":len({int(p["TEAM_ID"]) for p in players}),"player_team_stints":len(stints),"duplicate_rows":len(players)-len(unique),"unmatched_games":invalid_games})
player_pts=defaultdict(float)
for p in players:player_pts[(int(p["TEAM_ID"]),str(p["GAME_ID"]))]+=float(p["PTS"])
ptsmismatch=[(int(g["TEAM_ID"]),str(g["GAME_ID"])) for g in games if abs(player_pts[(int(g["TEAM_ID"]),str(g["GAME_ID"]))]-float(g["PTS"]))>.01]
check("player_points_match_team_scores",bool(players) and bool(games) and not ptsmismatch,{"mismatched_team_games":len(ptsmismatch),"sample":ptsmismatch[:10]})
traded=[pid for pid,v in teams_per_player.items() if len(v)>1]
check("traded_player_stints_preserved",bool(players) and len(traded)>0,{"multi_team_players":len(traded),"sample_ids":traded[:10],"method":"Aggregate by PLAYER_ID and TEAM_ID, never assign combined season totals to a final team."})
# Probe two teams before expanding to the full league. Stop if the source cannot
# supply historical dated game tables; avoid wasting requests on a failed source.
class ShortSession(requests.Session):
    def get(self,*args,**kwargs):
        kwargs["timeout"]=15
        return super().get(*args,**kwargs)
bet_report={"status":"testing","teams":{},"expected_teams":30,"source":"https://www.teamrankings.com/"}
report["sources"]["betting"]=bet_report
session=ShortSession()
session.headers["User-Agent"]="Mozilla/5.0"
ordered=["new-york-knicks","boston-celtics"]+[s for s in betting.TEAMS if s not in ("new-york-knicks","boston-celtics")]
def probe(slug):
    try:
        url,rows=betting.gather(session,slug,YEAR)
        (RAW/(slug+"-betting.json")).write_text(json.dumps(rows,indent=2))
        # The current parser permits playoffs; a matching regular-season game
        # key is required before accepting any betting lines.
        source_rows=byteam
        matches=set()
        for g in rows:
            for tid,gg in source_rows.items():
                if gg and betting.ALIASES.get(betting.norm(gg[0]["TEAM_NAME"]))==slug:
                    for x in gg:
                        if str(x["GAME_DATE"])[:10]==g["date"]:
                            matches.add(g["date"])
        bet_report["teams"][slug]={"status":"downloaded","games":len(rows),"games_with_spread":sum(g["spread"] is not None for g in rows),"games_with_total":sum(g["total"] is not None for g in rows),"source":url,"regular_season_dates_matched":len(matches)}
    except Exception as exc:
        bet_report["teams"][slug]={"status":"failed","error":str(exc)[:700]}
    print("betting",slug,json.dumps(bet_report["teams"][slug]),flush=True)
    save()
    time.sleep(1)
for i,slug in enumerate(ordered):
    if i==2 and all(bet_report["teams"][s]["status"]=="failed" for s in ordered[:2]):
        bet_report["status"]="source_probe_failed"
        bet_report["remaining_teams_not_requested"]=28
        break
    probe(slug)
else:bet_report["status"]="completed"
success=[x for x in bet_report["teams"].values() if x["status"]=="downloaded"]
check("betting_full_season_coverage",len(success)==30 and all(x["regular_season_dates_matched"]==82 and x["games_with_spread"]>=82 and x["games_with_total"]>=82 for x in success),{"downloaded_teams":len(success),"attempted_teams":len(bet_report["teams"]),"expected_teams":30})
report["finished_at"]=datetime.now(timezone.utc).isoformat()
report["basketball_passed"]=all(x["passed"] for k,x in report["checks"].items() if k!="betting_full_season_coverage")
report["all_sources_passed"]=all(x["passed"] for x in report["checks"].values())
save()
print("TEST_REPORT_START",flush=True)
print(json.dumps(report,indent=2),flush=True)
print("TEST_REPORT_END",flush=True)
