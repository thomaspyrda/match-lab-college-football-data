"""Adapters for frozen V15 rankings used by the CFB Dashboard."""
MODEL="v15"; UNIT_MODEL="validated_v15_recursive_dominance"
def index_rankings(payload):
 model=payload.get("model") or {}
 if model.get("version")!=MODEL:return {}
 return {r["team"]:r for r in payload.get("teams",[]) if r.get("team") and r.get("unit_strength_model")==UNIT_MODEL}
def team_card(r):
 return {"name":r.get("team"),"record":r.get("record"),"ap_rank":r.get("ap_rank"),"team_strength":r.get("strength_score"),"team_strength_rank":r.get("national_strength_rank"),"team_strength_sd":r.get("team_strength_sd"),"offensive_strength":r.get("offensive_strength"),"offensive_strength_rank":r.get("offensive_strength_rank"),"defensive_strength":r.get("defensive_strength"),"defensive_strength_rank":r.get("defensive_strength_rank"),"sos_rank":r.get("schedule_strength_rank"),"sos_score":r.get("schedule_strength_score"),"advanced":r.get("advanced") or {}}
METRICS=[("Overall Success Rate","overall_success","defensive_success"),("Passing Success","passing_success","defensive_passing_success"),("Rushing Success","rushing_success","defensive_rushing_success"),("Explosiveness","explosiveness","defensive_explosiveness"),("Finishing Drives","finishing_drives","defensive_finishing_drives"),("Third Down Conversion","third_down_conversion","defensive_third_down_conversion"),("Red Zone TD Rate","red_zone_td_rate","defensive_red_zone_td_rate")]
def matchup_metrics(away,home):
 a=away.get("advanced") or {};h=home.get("advanced") or {}
 return [{"label":label,"away_offense":a.get(off),"home_defense":h.get(de),"home_offense":h.get(off),"away_defense":a.get(de)} for label,off,de in METRICS]
def featured_mismatch(rows):
 out=[]
 for r in rows:
  for side,a,b in (("away_offense",r.get("away_offense"),r.get("home_defense")),("home_offense",r.get("home_offense"),r.get("away_defense"))):
   if isinstance(a,(int,float)) and isinstance(b,(int,float)):out.append((abs(a-b),r["label"],side,a,b))
 if not out:return None
 gap,label,side,a,b=max(out,key=lambda x:x[0])
 return {"metric":label,"side":side,"percentile_gap":round(gap,1),"offense_percentile":a,"opponent_defense_percentile":b}
