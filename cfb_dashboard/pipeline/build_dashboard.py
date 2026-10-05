#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from cfb_dashboard.pipeline.weather import game_weather
ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/"data"; OUT=ROOT/"cfb_dashboard"/"data"; OUT.mkdir(parents=True,exist_ok=True)
TEAM_META=DATA/"cfb_dashboard_team_metadata.json"; VENUE_META=DATA/"cfb_dashboard_venues.json"; PLAYER_USAGE=DATA/"cfb_dashboard_player_usage.json"; RAW_METRICS=DATA/"cfb_dashboard_raw_metrics.json"
ALIASES={"UConn":"Connecticut","Ole Miss":"Mississippi","UTSA":"Texas-San Antonio","Appalachian State":"App State","FIU":"Florida International","San Jose State":"San José State"}
def canon(x):return ALIASES.get(x,x)
METRICS=[
 ("Success Rate","Defensive Success Rate","overall_success","defensive_success","percent"),
 ("EPA / Play","EPA / Play Allowed","offensive_ppa","defensive_ppa","decimal"),
 ("Passing Success Rate","Defensive Pass Success Rate","passing_success","defensive_passing_success","percent"),
 ("Rushing Success Rate","Defensive Rush Success Rate","rushing_success","defensive_rushing_success","percent"),
 ("Explosiveness","Explosiveness Allowed","explosiveness","defensive_explosiveness","decimal"),
 ("Points per Opportunity","Points per Opportunity Allowed","points_per_opportunity","defensive_points_per_opportunity","decimal"),
 ("Third Down Conversion","Third Down Defense","third_down_conversion","defensive_third_down_conversion","percent"),
 ("Red Zone TD Rate","Red Zone TD Defense","red_zone_td_rate","defensive_red_zone_td_rate","percent"),
]
def team_payload(name,p,r):
 recent=p.get("recent_form") or {}; rec=r.get("record") or p.get("record")
 if not rec and recent.get("wins") is not None:rec=f"{recent.get('wins',0)}-{recent.get('losses',0)}"
 return {"name":name,"record":rec,"ap_rank":r.get("ap_rank",p.get("ap_rank")),"team_strength":r.get("strength_score",p.get("strength_score")),"team_strength_rank":r.get("national_strength_rank",p.get("national_strength_rank")),"team_strength_sd":r.get("team_strength_sd",p.get("team_strength_sd")),"offensive_strength":r.get("offensive_strength"),"offensive_strength_rank":r.get("offensive_strength_rank"),"defensive_strength":r.get("defensive_strength"),"defensive_strength_rank":r.get("defensive_strength_rank"),"sos_rank":r.get("schedule_strength_rank",p.get("schedule_strength_rank")),"form":recent,"metrics":(p.get("advanced") or {})|(r.get("dashboard_situational") or {})}
def metric_rows(a,h):
 rows=[]
 for off_label,def_label,off,de,fmt in METRICS:
  rows.append({
   "label":off_label,"offense_label":off_label,"defense_label":def_label,"format":fmt,
   "away_offense":(a.get("raw_metrics") or {}).get(off),
   "home_defense":(h.get("raw_metrics") or {}).get(de),
   "home_offense":(h.get("raw_metrics") or {}).get(off),
   "away_defense":(a.get("raw_metrics") or {}).get(de),
   "away_offense_rank":(a.get("raw_metrics") or {}).get(off+"_rank"),
   "home_defense_rank":(h.get("raw_metrics") or {}).get(de+"_rank"),
   "home_offense_rank":(h.get("raw_metrics") or {}).get(off+"_rank"),
   "away_defense_rank":(a.get("raw_metrics") or {}).get(de+"_rank"),
  })
 return rows
def edges(rows):
 out=[]
 for r in rows:
  pairs=[
   ("away","home",r.get("away_offense_rank"),r.get("home_defense_rank"),r.get("away_offense"),r.get("home_defense")),
   ("home","away",r.get("home_offense_rank"),r.get("away_defense_rank"),r.get("home_offense"),r.get("away_defense")),
  ]
  for offense_side,defense_side,off_rank,def_rank,off_value,def_value in pairs:
   if isinstance(off_rank,int) and isinstance(def_rank,int):
    offense_has_edge=off_rank<def_rank
    out.append({
     "metric":r["label"],"side":offense_side+"_offense","edge_side":offense_side if offense_has_edge else defense_side,
     "edge_unit":"offense" if offense_has_edge else "defense","rank_gap":abs(off_rank-def_rank),
     "offense_rank":off_rank,"opponent_defense_rank":def_rank,
     "offense_value":off_value,"opponent_defense_value":def_value
    })
 return sorted(out,key=lambda x:x["rank_gap"],reverse=True)
def mismatch(rows):
 e=edges(rows)
 if not e:return None
 x=e[0];return {"metric":x["metric"],"side":x["side"],"rank_gap":x["rank_gap"],"offense_rank":x["offense_rank"],"opponent_defense_rank":x["opponent_defense_rank"],"offense_value":x["offense_value"],"opponent_defense_value":x["opponent_defense_value"]}
def build_trends(a,h,rows,context=None):
 out=[]; side_names={"away":a["name"],"home":h["name"]}
 for x in edges(rows):
  if len(out)>=5:break
  if x["rank_gap"]>=12:out.append({"type":"matchup_edge","metric":x["metric"],"team":side_names[x["edge_side"]],"edge_unit":x["edge_unit"],"offense_side":x["side"].split("_")[0],"direction":"rank gap","gap":x["rank_gap"]})
 context=context or {}
 if a.get("ap_rank") and not h.get("ap_rank"):out.append({"type":"ranked_context","team":a["name"],"detail":"ranked road team vs unranked home opponent"})
 elif h.get("ap_rank") and not a.get("ap_rank"):out.append({"type":"ranked_context","team":h["name"],"detail":"ranked home team vs unranked road opponent"})
 if (a.get("form") or {}).get("coming_off_loss") is True:out.append({"type":"bounce_back","team":a["name"],"detail":"coming off a loss"})
 if (h.get("form") or {}).get("coming_off_loss") is True:out.append({"type":"bounce_back","team":h["name"],"detail":"coming off a loss"})
 if context.get("conference_game") is True:out.append({"type":"game_context","detail":"conference matchup"})
 if context.get("neutral_site") is True:out.append({"type":"game_context","detail":"neutral-site matchup"})
 ar,hr=a.get("team_strength_rank"),h.get("team_strength_rank")
 if isinstance(ar,int) and isinstance(hr,int) and abs(ar-hr)>=20:out.append({"type":"strength_gap","team":a["name"] if ar<hr else h["name"],"rank_gap":abs(ar-hr)})
 return out[:8]
def load_map(path,key):
 if not path.exists():return {}
 return json.loads(path.read_text(encoding="utf-8")).get(key) or {}
def market_record(team,games,kind,location=None):
 w=l=p=0
 for g in games:
  r=g.get("result") or {}
  if not r:continue
  home=canon(g.get("home")); away=canon(g.get("away")); key=canon(team)
  if key not in (home,away):continue
  side="home" if key==home else "away"
  if location and g.get("neutral_site"):continue
  if location and side!=location:continue
  if kind=="ats":
   outcome=r.get("ats")
   if outcome=="push":p+=1
   elif outcome=="home_cover":w+=1 if side=="home" else 0;l+=1 if side=="away" else 0
   elif outcome=="away_cover":w+=1 if side=="away" else 0;l+=1 if side=="home" else 0
  else:
   outcome=r.get("total")
   if outcome=="push":p+=1
   elif outcome=="over":w+=1
   elif outcome=="under":l+=1
 return f"{w}-{l}-{p}"
def market_trends(away,home,games):
 return [
  {"label":"ATS this season","away":market_record(away["name"],games,"ats"),"home":market_record(home["name"],games,"ats"),"note":"Current-season ATS record using available closing lines."},
  {"label":"ATS by location","away":"Road · "+market_record(away["name"],games,"ats","away"),"home":"Home · "+market_record(home["name"],games,"ats","home"),"note":"Current-season ATS record in the same home/road role as this matchup."},
  {"label":"O/U this season","away":market_record(away["name"],games,"ou"),"home":market_record(home["name"],games,"ou"),"note":"Current-season over-under record. Format is Over-Under-Push."},
  {"label":"O/U by location","away":"Road · "+market_record(away["name"],games,"ou","away"),"home":"Home · "+market_record(home["name"],games,"ou","home"),"note":"Current-season over-under record in the same home/road role as this matchup."},
 ]
def player_cards(team,usage_map):
 rows=usage_map.get(canon(team["name"]),[])[:4]
 out=[]
 for i,row in enumerate(rows):
  out.append({"team":team.get("abbr") or team.get("abbreviation") or team["name"],"name":row.get("name") or f"Usage player {i+1}","position":row.get("position") or "—","usage":[{"label":"Overall usage","value":row.get("overall")},{"label":"Pass usage","value":row.get("pass")},{"label":"Rush usage","value":row.get("rush")},{"label":"3rd-down usage","value":row.get("third_down")}],"placeholder":False})
 while len(out)<4:
  out.append({"team":team.get("abbr") or team.get("abbreviation") or team["name"],"name":"Usage data pending","position":"—","usage":[],"placeholder":True})
 return out
def enrich_form_abbreviations(team,team_meta):
 form=team.get("form") or {}
 for game in form.get("last_five") or []:
  meta=team_meta.get(canon(game.get("opponent"))) or {}
  game["opponent_abbr"]=meta.get("abbr") or meta.get("abbreviation")
 return team
def parse_kickoff(v):
 try:return datetime.fromisoformat(str(v).replace("Z","+00:00")) if v else None
 except ValueError:return None
def main():
 upcoming=json.loads((DATA/"upcoming.json").read_text()); rankings=json.loads((DATA/"current_rankings.json").read_text())
 by={canon(x["team"]):x for x in rankings.get("teams",[])}; tm={canon(k):v for k,v in load_map(TEAM_META,"teams").items()}; vm=load_map(VENUE_META,"venues"); usage={canon(k):v for k,v in load_map(PLAYER_USAGE,"teams").items()}; raw={canon(k):v for k,v in load_map(RAW_METRICS,"teams").items()}; hist_path=DATA/"historical"/f"{rankings.get('season')}.json"; season_games=(json.loads(hist_path.read_text(encoding="utf-8")).get("games") or []) if hist_path.exists() else []; games=[]
 for g in upcoming.get("games",[]):
  ap=g.get("away_profile") or {}; hp=g.get("home_profile") or {}; ar=by.get(canon(g["away"]),{}); hr=by.get(canon(g["home"]),{})
  away=team_payload(g["away"],ap,ar)|{"conference":g.get("away_conference"),"espn_id":g.get("away_id"),"raw_metrics":raw.get(canon(g["away"]),{})}|tm.get(canon(g["away"]),{})
  home=team_payload(g["home"],hp,hr)|{"conference":g.get("home_conference"),"espn_id":g.get("home_id"),"raw_metrics":raw.get(canon(g["home"]),{})}|tm.get(canon(g["home"]),{})
  away=enrich_form_abbreviations(away,tm); home=enrich_form_abbreviations(home,tm)
  rows=metric_rows(away,home); venue=vm.get(str(g.get("venue_id"))) or vm.get(str(g.get("venue"))) or {}; ko=parse_kickoff(g.get("start_date")); weather={"summary":game_weather(venue,ko,bool(g.get("neutral_site")))} if ko else {"summary":"Forecast unavailable"}
  games.append({"game_id":g.get("game_id"),"season":g.get("season"),"week":g.get("week"),"kickoff":g.get("start_date"),"venue":g.get("venue"),"venue_id":g.get("venue_id"),"away":away,"home":home,"market":{"spread":g.get("spread"),"total":g.get("over_under"),"home_moneyline":g.get("home_moneyline"),"away_moneyline":g.get("away_moneyline"),"provider":g.get("provider")},"context":{"conference_game":g.get("conference_game"),"neutral_site":g.get("neutral_site")},"weather":weather,"matchup_metrics":rows,"featured_mismatch":mismatch(rows),"market_trends":market_trends(away,home,season_games),"players":player_cards(away,usage)+player_cards(home,usage),"trends":build_trends(away,home,rows,{"conference_game":g.get("conference_game"),"neutral_site":g.get("neutral_site")})})
 payload={"slate":{"season":rankings.get("season"),"week":rankings.get("week"),"generated_at":datetime.now(timezone.utc).isoformat(),"model_version":(rankings.get("model") or {}).get("version")},"games":games}; (OUT/"dashboard.json").write_text(json.dumps(payload,indent=2),encoding="utf-8");print(f"Built {len(games)} CFB Dashboard matchups")
if __name__=="__main__":main()