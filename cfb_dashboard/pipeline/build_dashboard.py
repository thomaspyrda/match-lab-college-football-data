#!/usr/bin/env python3
"""Build the first browser-ready CFB Dashboard artifact from existing Match Lab output.

No provider calls occur here. This consumes already-cached, pregame-safe Match Lab
artifacts so dashboard development cannot expose CFBD credentials or change V15.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"data"
OUT=ROOT/"cfb_dashboard"/"data"
OUT.mkdir(parents=True,exist_ok=True)

ALIASES={"UConn":"Connecticut","Ole Miss":"Mississippi","UTSA":"Texas-San Antonio","Appalachian State":"App State","FIU":"Florida International","San Jose State":"San José State"}
def canon(x): return ALIASES.get(x,x)

METRICS=[
 ("Overall Success Rate","overall_success","defensive_success"),
 ("Offensive Efficiency","offensive_efficiency","defensive_efficiency"),
 ("Passing Success","passing_success","defensive_passing_success"),
 ("Rushing Success","rushing_success","defensive_rushing_success"),
 ("Passing PPA","passing_ppa","defensive_passing_ppa"),
 ("Rushing PPA","rushing_ppa","defensive_rushing_ppa"),
 ("Explosiveness","explosiveness","defensive_explosiveness"),
 ("Finishing Drives","finishing_drives","defensive_finishing_drives"),
 ("Standard Down Success","standard_down_success","defensive_standard_down_success"),
 ("Passing Down Success","passing_down_success","defensive_passing_down_success"),
 ("Line Yards","line_yards","defensive_line_yards"),
 ("Stuff Rate","stuff_rate","defensive_stuff_rate"),
 ("Power Success","power_success","defensive_power_success"),
]

def pct(profile,key):
    return (profile.get("advanced") or {}).get(key)

def team_payload(name, profile, ranking):
    recent=profile.get("recent_form") or {}
    rec=ranking.get("record") or profile.get("record")
    if not rec and recent.get("wins") is not None:
        rec=f"{recent.get('wins',0)}-{recent.get('losses',0)}"
    return {
      "name":name,
      "record":rec,
      "ap_rank":profile.get("ap_rank"),
      "team_strength":ranking.get("strength_score",profile.get("strength_score")),
      "team_strength_rank":ranking.get("national_strength_rank",profile.get("national_strength_rank")),
      "team_strength_sd":ranking.get("team_strength_sd",profile.get("team_strength_sd")),
      "offensive_strength":ranking.get("offensive_strength"),
      "offensive_strength_rank":ranking.get("offensive_strength_rank"),
      "defensive_strength":ranking.get("defensive_strength"),
      "defensive_strength_rank":ranking.get("defensive_strength_rank"),
      "sos_rank":ranking.get("schedule_strength_rank",profile.get("schedule_strength_rank")),
      "form":recent,
      "metrics":profile.get("advanced") or {},
    }

def metric_rows(away,home):
    rows=[]
    for label,off,defn in METRICS:
        rows.append({
          "label":label,
          "away_offense":pct(away,off),
          "home_defense":pct(home,defn),
          "home_offense":pct(home,off),
          "away_defense":pct(away,defn),
        })
    return rows

def matchup_edges(rows):
    candidates=[]
    for r in rows:
        for side,a,b in (("away_offense",r["away_offense"],r["home_defense"]),("home_offense",r["home_offense"],r["away_defense"])):
            if isinstance(a,(int,float)) and isinstance(b,(int,float)):
                candidates.append({"metric":r["label"],"side":side,"gap":round(a-b,1),"magnitude":round(abs(a-b),1),"offense_value":a,"opponent_defense_value":b})
    return sorted(candidates,key=lambda x:x["magnitude"],reverse=True)

def mismatch(rows):
    edges=matchup_edges(rows)
    if not edges:return None
    x=edges[0]
    return {"metric":x["metric"],"side":x["side"],"percentile_gap":x["magnitude"],"offense_percentile":x["offense_value"],"opponent_defense_percentile":x["opponent_defense_value"]}

def build_trends(away,home,rows):
    edges=matchup_edges(rows); out=[]
    names={"away_offense":away["name"],"home_offense":home["name"]}
    for x in edges:
        if len(out)>=5:break
        if x["magnitude"]<12:continue
        direction="advantage" if x["gap"]>0 else "disadvantage"
        out.append({"type":"matchup_edge","metric":x["metric"],"team":names[x["side"]],"direction":direction,"gap":x["magnitude"]})
    ar,hr=away.get("team_strength_rank"),home.get("team_strength_rank")
    if isinstance(ar,int) and isinstance(hr,int) and abs(ar-hr)>=20:
        stronger=away["name"] if ar<hr else home["name"]; diff=abs(ar-hr)
        out.append({"type":"strength_gap","team":stronger,"rank_gap":diff})
    return out[:6]

def main():
    upcoming=json.loads((DATA/"upcoming.json").read_text())
    rankings=json.loads((DATA/"current_rankings.json").read_text())
    by_team={canon(x["team"]):x for x in rankings.get("teams",[])}
    games=[]
    for g in upcoming.get("games",[]):
        awayp=g.get("away_profile") or {}; homep=g.get("home_profile") or {}
        awayr=by_team.get(canon(g["away"]),{}); homer=by_team.get(canon(g["home"]),{})
        metrics=metric_rows(awayp,homep)
        games.append({
          "game_id":g.get("game_id"),"season":g.get("season"),"week":g.get("week"),
          "kickoff":g.get("start_date"),"venue":g.get("venue"),
          "away":team_payload(g["away"],awayp,awayr)|{"conference":g.get("away_conference")},
          "home":team_payload(g["home"],homep,homer)|{"conference":g.get("home_conference")},
          "market":{"spread":g.get("spread"),"total":g.get("over_under"),"home_moneyline":g.get("home_moneyline"),"away_moneyline":g.get("away_moneyline"),"provider":g.get("provider")},
          "context":{"conference_game":g.get("conference_game"),"neutral_site":g.get("neutral_site")},
          "weather":{},"matchup_metrics":metrics,"featured_mismatch":mismatch(metrics),"trends":build_trends(away,home,metrics)
        })
    payload={"slate":{"season":rankings.get("season"),"week":rankings.get("week"),"generated_at":datetime.now(timezone.utc).isoformat(),"model_version":(rankings.get("model") or {}).get("version")},"games":games}
    (OUT/"dashboard.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    print(f"Built {len(games)} CFB Dashboard matchups for Week {payload['slate']['week']}")

if __name__=="__main__":main()