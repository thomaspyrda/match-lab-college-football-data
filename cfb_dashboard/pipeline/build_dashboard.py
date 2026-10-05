#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from cfb_dashboard.pipeline.weather import game_weather
ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/"data"; OUT=ROOT/"cfb_dashboard"/"data"; OUT.mkdir(parents=True,exist_ok=True)
TEAM_META=DATA/"cfb_dashboard_team_metadata.json"; VENUE_META=DATA/"cfb_dashboard_venues.json"
ALIASES={"UConn":"Connecticut","Ole Miss":"Mississippi","UTSA":"Texas-San Antonio","Appalachian State":"App State","FIU":"Florida International","San Jose State":"San José State"}
def canon(x):return ALIASES.get(x,x)
METRICS=[("Overall Success Rate","overall_success","defensive_success"),("Offensive Efficiency","offensive_efficiency","defensive_efficiency"),("Passing Success","passing_success","defensive_passing_success"),("Rushing Success","rushing_success","defensive_rushing_success"),("Passing PPA","passing_ppa","defensive_passing_ppa"),("Rushing PPA","rushing_ppa","defensive_rushing_ppa"),("Explosiveness","explosiveness","defensive_explosiveness"),("Finishing Drives","finishing_drives","defensive_finishing_drives"),("Standard Down Success","standard_down_success","defensive_standard_down_success"),("Passing Down Success","passing_down_success","defensive_passing_down_success"),("Line Yards","line_yards","defensive_line_yards"),("Stuff Rate","stuff_rate","defensive_stuff_rate"),("Power Success","power_success","defensive_power_success"),("Third Down Conversion","third_down_conversion","defensive_third_down_conversion"),("Red Zone TD Rate","red_zone_td_rate","defensive_red_zone_td_rate"),("Red Zone Points / Trip","red_zone_points_per_trip","defensive_red_zone_points_per_trip")]
def pct(p,k):return (p.get("advanced") or {}).get(k)
def team_payload(name,p,r):
 recent=p.get("recent_form") or {}; rec=r.get("record") or p.get("record")
 if not rec and recent.get("wins") is not None:rec=f"{recent.get('wins',0)}-{recent.get('losses',0)}"
 return {"name":name,"record":rec,"ap_rank":p.get("ap_rank"),"team_strength":r.get("strength_score",p.get("strength_score")),"team_strength_rank":r.get("national_strength_rank",p.get("national_strength_rank")),"team_strength_sd":r.get("team_strength_sd",p.get("team_strength_sd")),"offensive_strength":r.get("offensive_strength"),"offensive_strength_rank":r.get("offensive_strength_rank"),"defensive_strength":r.get("defensive_strength"),"defensive_strength_rank":r.get("defensive_strength_rank"),"sos_rank":r.get("schedule_strength_rank",p.get("schedule_strength_rank")),"form":recent,"metrics":(p.get("advanced") or {})|(r.get("dashboard_situational") or {})}
def metric_rows(a,h):
 return [{"label":label,"away_offense":pct(a,off),"home_defense":pct(h,de),"home_offense":pct(h,off),"away_defense":pct(a,de)} for label,off,de in METRICS]
def edges(rows):
 out=[]
 for r in rows:
  for side,a,b in (("away_offense",r["away_offense"],r["home_defense"]),("home_offense",r["home_offense"],r["away_defense"])):
   if isinstance(a,(int,float)) and isinstance(b,(int,float)):out.append({"metric":r["label"],"side":side,"gap":round(a-b,1),"magnitude":round(abs(a-b),1),"offense_value":a,"opponent_defense_value":b})
 return sorted(out,key=lambda x:x["magnitude"],reverse=True)
def mismatch(rows):
 e=edges(rows)
 if not e:return None
 x=e[0];return {"metric":x["metric"],"side":x["side"],"percentile_gap":x["magnitude"],"offense_percentile":x["offense_value"],"opponent_defense_percentile":x["opponent_defense_value"]}
def build_trends(a,h,rows):
 out=[]; names={"away_offense":a["name"],"home_offense":h["name"]}
 for x in edges(rows):
  if len(out)>=5:break
  if x["magnitude"]>=12:out.append({"type":"matchup_edge","metric":x["metric"],"team":names[x["side"]],"direction":"advantage" if x["gap"]>0 else "disadvantage","gap":x["magnitude"]})
 ar,hr=a.get("team_strength_rank"),h.get("team_strength_rank")
 if isinstance(ar,int) and isinstance(hr,int) and abs(ar-hr)>=20:out.append({"type":"strength_gap","team":a["name"] if ar<hr else h["name"],"rank_gap":abs(ar-hr)})
 return out[:6]
def load_map(path,key):
 if not path.exists():return {}
 return json.loads(path.read_text(encoding="utf-8")).get(key) or {}
def parse_kickoff(v):
 try:return datetime.fromisoformat(str(v).replace("Z","+00:00")) if v else None
 except ValueError:return None
def main():
 upcoming=json.loads((DATA/"upcoming.json").read_text()); rankings=json.loads((DATA/"current_rankings.json").read_text())
 by={canon(x["team"]):x for x in rankings.get("teams",[])}; tm={canon(k):v for k,v in load_map(TEAM_META,"teams").items()}; vm=load_map(VENUE_META,"venues"); games=[]
 for g in upcoming.get("games",[]):
  ap=g.get("away_profile") or {}; hp=g.get("home_profile") or {}; ar=by.get(canon(g["away"]),{}); hr=by.get(canon(g["home"]),{})
  away=team_payload(g["away"],ap,ar)|{"conference":g.get("away_conference")}|tm.get(canon(g["away"]),{}); home=team_payload(g["home"],hp,hr)|{"conference":g.get("home_conference")}|tm.get(canon(g["home"]),{})
  rows=metric_rows({"advanced":away["metrics"]},{"advanced":home["metrics"]}); venue=vm.get(str(g.get("venue_id"))) or vm.get(str(g.get("venue"))) or {}; ko=parse_kickoff(g.get("start_date")); weather={"summary":game_weather(venue,ko,bool(g.get("neutral_site")))} if ko else {"summary":"Forecast unavailable"}
  games.append({"game_id":g.get("game_id"),"season":g.get("season"),"week":g.get("week"),"kickoff":g.get("start_date"),"venue":g.get("venue"),"venue_id":g.get("venue_id"),"away":away,"home":home,"market":{"spread":g.get("spread"),"total":g.get("over_under"),"home_moneyline":g.get("home_moneyline"),"away_moneyline":g.get("away_moneyline"),"provider":g.get("provider")},"context":{"conference_game":g.get("conference_game"),"neutral_site":g.get("neutral_site")},"weather":weather,"matchup_metrics":rows,"featured_mismatch":mismatch(rows),"trends":build_trends(away,home,rows)})
 payload={"slate":{"season":rankings.get("season"),"week":rankings.get("week"),"generated_at":datetime.now(timezone.utc).isoformat(),"model_version":(rankings.get("model") or {}).get("version")},"games":games}; (OUT/"dashboard.json").write_text(json.dumps(payload,indent=2),encoding="utf-8");print(f"Built {len(games)} CFB Dashboard matchups")
if __name__=="__main__":main()
