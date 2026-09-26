#!/usr/bin/env python3
import csv,json,os,urllib.parse,urllib.request
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parent; DATA=ROOT/"data"; (DATA/"historical").mkdir(parents=True,exist_ok=True)
KEY=os.environ.get("CFBD_API_KEY")
if not KEY: raise SystemExit("CFBD_API_KEY secret is required")
def api(path,**params):
 url="https://api.collegefootballdata.com"+path+"?"+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"MatchLab/1.0"})
 with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
def dt(v):
 try:return datetime.fromisoformat((v or "").replace("Z","+00:00"))
 except:return datetime.min.replace(tzinfo=timezone.utc)
def pickline(entry):
 providers=entry.get("lines") or []
 pref=next((x for x in providers if str(x.get("provider","")).lower()=="consensus"),None)
 return pref or next((x for x in providers if x.get("spread") is not None or x.get("overUnder") is not None),None) or (providers[0] if providers else {})
def num(v):
 try:return float(v) if v is not None else None
 except:return None
def result(team,g):
 hp=g.get("homePoints");ap=g.get("awayPoints")
 if hp is None or ap is None:return None
 home=g.get("homeTeam")==team; won=(hp>ap) if home else (ap>hp)
 return {"won":won,"points":hp if home else ap,"allowed":ap if home else hp}
def form(team,prior):
 rr=[result(team,g) for g in prior];rr=[x for x in rr if x]
 return {"games":len(rr),"wins":sum(x["won"] for x in rr),"losses":sum(not x["won"] for x in rr),"avg_points":round(sum(x["points"] for x in rr)/len(rr),1) if rr else None,"avg_allowed":round(sum(x["allowed"] for x in rr)/len(rr),1) if rr else None,"coming_off_loss":(not rr[-1]["won"]) if rr else None}
strength={}
for p in (DATA/"weekly").glob("*.json"):
 d=json.loads(p.read_text());strength[int(d["season"])]=d["weeks"]
advanced={}
for p in (DATA/"profiles").glob("*.json"):
 d=json.loads(p.read_text());advanced[int(d["season"])]=d.get("weeks",{})

# Compounded weekly power rating.
# Week 1 begins from the preseason full-FBS strength board. After each completed
# week, teams move up/down based on (1) opponent quality and (2) game performance.
# No week is recalculated from scratch and no future result enters a pregame board.
FCS_OTHER_STRENGTH=15.0
RATING_TO_POINTS=0.30
HOME_FIELD_POINTS=2.5
UPDATE_RATE=0.32
MAX_GAME_DELTA=12.0
MARGIN_CAP=42.0

TEAM_ALIASES={
 "UConn":"Connecticut",
 "Connecticut":"Connecticut",
}
def canon_team(team):
 return TEAM_ALIASES.get(team,team)

def tier(score):
 return "Elite" if score>=90 else "Strong" if score>=75 else "Above Average" if score>=50 else "Below Average" if score>=25 else "Weak"

def pct_score(value,values):
 usable=[float(v) for v in values if v is not None]
 if value is None or len(usable)<2:return None
 value=float(value);below=sum(v<value for v in usable);tied=sum(v==value for v in usable)
 return max(1,min(100,int(100*(below+(tied-1)/2)/(len(usable)-1)+0.5)))

def preseason_board(year):
 weeks=strength.get(year,{})
 if not weeks:return {}
 first_week=min((int(w) for w in weeks),default=1)
 teams=weeks.get(str(first_week),{}).get("teams",{})
 out={}
 for team,row in teams.items():
  score=row.get("strength_score")
  if score is not None:out[canon_team(team)]=float(score)
 return out

def ap_for_week(year,week,team):
 rows=strength.get(year,{}).get(str(week),{}).get("teams",{})
 direct=rows.get(team)
 if direct:return direct.get("ap_rank")
 key=canon_team(team)
 for name,row in rows.items():
  if canon_team(name)==key:return row.get("ap_rank")
 return None

def build_compounded_boards(year,games):
 ratings=preseason_board(year)
 if not ratings:return {}
 preseason=dict(ratings)
 opponent_log={team:[] for team in ratings}
 games_played={team:0 for team in ratings}
 max_week=max([int(g.get("week") or 0) for g in games] or [1])
 by_week=defaultdict(list)
 for g in games:
  if g.get("homePoints") is None or g.get("awayPoints") is None:continue
  by_week[int(g.get("week") or 0)].append(g)

 boards={}
 for week in range(1,max_week+2):
  teams=sorted(ratings)
  values=[ratings[t] for t in teams]
  sos_raw={t:(sum(opponent_log[t])/len(opponent_log[t]) if opponent_log[t] else None) for t in teams}
  sos_values=[v for v in sos_raw.values() if v is not None]
  ranked=sorted(teams,key=lambda t:(-ratings[t],t))
  rank_map={};last=None;rank=0
  for pos,t in enumerate(ranked,1):
   if ratings[t]!=last:rank=pos;last=ratings[t]
   rank_map[t]=rank

  board={}
  for t in teams:
   score=pct_score(ratings[t],values)
   board[t]={
    "national_strength_rank":rank_map[t],
    "fbs_field_size":len(teams),
    "strength_score":score,
    "strength_tier":tier(score),
    "top_percent":101-score,
    "strength_source":"compounded_weekly_power",
    "power_rating":round(ratings[t],2),
    "preseason_strength":round(preseason[t],2),
    "schedule_strength":round(sos_raw[t],2) if sos_raw[t] is not None else None,
    "schedule_strength_score":pct_score(sos_raw[t],sos_values) if sos_raw[t] is not None else None,
    "games_in_rating":games_played[t],
   }
  boards[str(week)]=board

  # All games in a week are graded against the same pregame snapshot so the
  # weekly board is stable and strictly pregame-safe.
  pre=dict(ratings);deltas=defaultdict(list)
  for g in sorted(by_week.get(week,[]),key=lambda x:x.get("startDate") or ""):
   hp=float(g.get("homePoints"));ap=float(g.get("awayPoints"))
   home=canon_team(g.get("homeTeam"));away=canon_team(g.get("awayTeam"))
   for team,opp,is_home,margin in (
    (home,away,True,hp-ap),
    (away,home,False,ap-hp),
   ):
    if team not in pre:continue
    team_rating=pre[team]
    opp_rating=pre.get(opp,FCS_OTHER_STRENGTH)
    capped=max(-MARGIN_CAP,min(MARGIN_CAP,margin))
    expected=(team_rating-opp_rating)*RATING_TO_POINTS+(HOME_FIELD_POINTS if is_home else -HOME_FIELD_POINTS)
    surprise=capped-expected
    delta=max(-MAX_GAME_DELTA,min(MAX_GAME_DELTA,UPDATE_RATE*surprise))
    deltas[team].append(delta)
    opponent_log[team].append(float(opp_rating))
    games_played[team]+=1

  for team,team_deltas in deltas.items():
   ratings[team]=pre[team]+sum(team_deltas)/len(team_deltas)

 return boards

power_boards={}
def srank(year,week,team):
 board=power_boards.get(year,{})
 row=board.get(str(week),{}).get(canon_team(team))
 if row is None and board:
  prior=[int(w) for w in board if int(w)<=int(week)]
  if prior:row=board[str(max(prior))].get(canon_team(team))
 if not row:return {"ap_rank":ap_for_week(year,week,team)}
 return {"ap_rank":ap_for_week(year,week,team)}|row

def adv(year,week,team):
 board=advanced.get(year,{}).get(str(week),{})
 r=board.get("teams",{}).get(team)
 return (r|{"through_week":board.get("through_week")}) if r else None
all_upcoming=[]; now=datetime.now(timezone.utc); end=now+timedelta(days=7)
for year in sorted(strength):
 games=api("/games",year=year,seasonType="regular")
 power_boards[year]=build_compounded_boards(year,games)
 lines=api("/lines",year=year,seasonType="regular")
 lm={str(x.get("id")):pickline(x) for x in lines}
 histories=defaultdict(list); records=[]
 for g in sorted(games,key=lambda x:dt(x.get("startDate"))):
  gid=str(g.get("id"));week=int(g.get("week") or 0);home=g.get("homeTeam");away=g.get("awayTeam")
  if not home or not away:continue
  line=lm.get(gid,{})
  hs=srank(year,week,home);as_=srank(year,week,away)
  if hs.get("national_strength_rank") is None and as_.get("national_strength_rank") is None:continue
  hs["classification"]="FBS" if hs.get("national_strength_rank") is not None else "FCS/Other"
  as_["classification"]="FBS" if as_.get("national_strength_rank") is not None else "FCS/Other"
  hf=form(home,histories[home]);af=form(away,histories[away])
  spread=num(line.get("spread"));total=num(line.get("overUnder"));hml=num(line.get("homeMoneyline"));aml=num(line.get("awayMoneyline"))
  hp=g.get("homePoints");ap=g.get("awayPoints");completed=hp is not None and ap is not None
  fav_side=None
  if spread is not None:fav_side="home" if spread<0 else ("away" if spread>0 else None)
  ats=None
  if completed and spread is not None:
   adj=float(hp)+spread-float(ap);ats="home_cover" if adj>0 else ("away_cover" if adj<0 else "push")
  ou=None
  if completed and total is not None:
   s=float(hp)+float(ap);ou="over" if s>total else ("under" if s<total else "push")
  rec={"game_id":gid,"season":year,"week":week,"start_date":g.get("startDate"),"home":home,"away":away,"home_id":g.get("homeId"),"away_id":g.get("awayId"),"home_conference":g.get("homeConference"),"away_conference":g.get("awayConference"),"conference_game":bool(g.get("conferenceGame")),"neutral_site":bool(g.get("neutralSite")),"spread":spread,"over_under":total,"home_moneyline":hml,"away_moneyline":aml,"provider":line.get("provider"),"home_profile":hs|{"recent_form":hf,"advanced":adv(year,week,home)},"away_profile":as_|{"recent_form":af,"advanced":adv(year,week,away)},"favorite_side":fav_side,"result":{"home_points":hp,"away_points":ap,"ats":ats,"total":ou} if completed else None}
  records.append(rec)
  kickoff=dt(g.get("startDate"))
  if year==now.year and now<=kickoff<=end: all_upcoming.append(rec|{"result":None})
  if completed:histories[home].append(g);histories[away].append(g)
 (DATA/"historical"/f"{year}.json").write_text(json.dumps({"season":year,"games":records},separators=(",",":")),encoding="utf-8")
# CFBD's season-wide games response may omit future weeks. Request the next
# two weeks explicitly, then build their live AP and full-field strength boards.
current_records=json.loads((DATA/"historical"/f"{now.year}.json").read_text())["games"]
# Determine the weeks that actually intersect the rolling seven-day window.
# Do not use max(schedule week)+1: CFBD may return the full future schedule,
# which would incorrectly jump to the end of the season and publish zero games.
scheduled_weeks={
 int(g.get("week") or 0) for g in current_records
 if now<=dt(g.get("start_date"))<=end and int(g.get("week") or 0)>0
}
last_completed=max((int(g.get("week") or 0) for g in current_records if g.get("result")),default=0)
candidate_weeks=sorted(scheduled_weeks | {last_completed+1,last_completed+2})
rankings=api("/rankings",year=now.year,seasonType="regular")
def live_ap(week):
 snap=next((x for x in rankings if int(x.get("week") or 0)==week),None)
 poll=next((p for p in (snap or {}).get("polls",[]) if str(p.get("poll","")).lower() in ("ap top 25","ap")),None)
 return {r.get("school"):int(r["rank"]) for r in (poll or {}).get("ranks",[]) if r.get("school")}
def live_strength(week):
 ap=live_ap(week)
 board=power_boards.get(now.year,{})
 rows=board.get(str(week))
 if rows is None and board:
  prior=[int(w) for w in board if int(w)<=int(week)]
  rows=board.get(str(max(prior)),{}) if prior else {}
 out={}
 for team,row in (rows or {}).items():
  out[team]=row|{"ap_rank":ap.get(team) or (ap.get("UConn") if team=="Connecticut" else None)}
  if team=="Connecticut":
   out["UConn"]=out.pop("Connecticut")
 return out

all_upcoming=[]
for week in candidate_weeks:
 future=api("/games",year=now.year,seasonType="regular",week=week)
 future_lines=api("/lines",year=now.year,seasonType="regular",week=week)
 fl={str(x.get("id")):pickline(x) for x in future_lines}; board=live_strength(week)
 for g in future:
  kickoff=dt(g.get("startDate"))
  if not (now<=kickoff<=end):continue
  home=g.get("homeTeam");away=g.get("awayTeam");line=fl.get(str(g.get("id")),{})
  hp=board.get(home,{});ap=board.get(away,{})
  if hp.get("national_strength_rank") is None and ap.get("national_strength_rank") is None: continue
  hp["classification"]="FBS" if hp.get("national_strength_rank") is not None else "FCS/Other"
  ap["classification"]="FBS" if ap.get("national_strength_rank") is not None else "FCS/Other"
  home_prior=[x for x in games if (x.get("homeTeam")==home or x.get("awayTeam")==home) and x.get("homePoints") is not None and dt(x.get("startDate"))<kickoff]
  away_prior=[x for x in games if (x.get("homeTeam")==away or x.get("awayTeam")==away) and x.get("homePoints") is not None and dt(x.get("startDate"))<kickoff]
  all_upcoming.append({"game_id":str(g.get("id")),"season":now.year,"week":week,"start_date":g.get("startDate"),"home":home,"away":away,"home_id":g.get("homeId"),"away_id":g.get("awayId"),"home_conference":g.get("homeConference"),"away_conference":g.get("awayConference"),"conference_game":bool(g.get("conferenceGame")),"neutral_site":bool(g.get("neutralSite")),"spread":num(line.get("spread")),"over_under":num(line.get("overUnder")),"home_moneyline":num(line.get("homeMoneyline")),"away_moneyline":num(line.get("awayMoneyline")),"provider":line.get("provider"),"home_profile":hp|{"recent_form":form(home,home_prior),"advanced":adv(now.year,week,home)},"away_profile":ap|{"recent_form":form(away,away_prior),"advanced":adv(now.year,week,away)},"favorite_side":"home" if num(line.get("spread")) is not None and num(line.get("spread"))<0 else ("away" if num(line.get("spread")) is not None and num(line.get("spread"))>0 else None),"result":None})
(DATA/"upcoming.json").write_text(json.dumps({"generated_at":now.isoformat(),"window_end":end.isoformat(),"games":sorted(all_upcoming,key=lambda x:x["start_date"] or "")},indent=2),encoding="utf-8")

# Publish a current-to-date full-FBS strength snapshot.
# Unlike historical matchup snapshots, this live board intentionally includes every
# completed game available at build time, including games already finished in the
# current week. Historical matchup pages remain strictly pregame-safe.
current_week=max(1,last_completed+1)
current_board=live_strength(current_week)

OFFENSE_WEIGHTS={
 "offensive_efficiency":0.30,
 "rushing_success":0.15,
 "passing_success":0.20,
 "explosiveness":0.15,
 "finishing_drives":0.20,
}
DEFENSE_WEIGHTS={
 "defensive_efficiency":0.30,
 "defensive_rushing_success":0.15,
 "defensive_passing_success":0.20,
 "defensive_explosiveness":0.15,
 "defensive_finishing_drives":0.10,
 "havoc":0.10,
}

def weighted_unit_score(profile,weights):
 if not profile:return None
 pairs=[(profile.get(k),w) for k,w in weights.items() if profile.get(k) is not None]
 if not pairs:return None
 total=sum(w for _,w in pairs)
 return sum(float(v)*w for v,w in pairs)/total if total else None

def opponent_multiplier(opponent_unit_score):
 # Smooth 0.80x-1.20x curve centered near the FBS median.
 if opponent_unit_score is None:return 1.0
 return 0.80+0.40*((max(1.0,min(100.0,float(opponent_unit_score)))-1.0)/99.0)

profiles={team:adv(now.year,current_week,team) for team in current_board}
off_base={team:weighted_unit_score(profile,OFFENSE_WEIGHTS) for team,profile in profiles.items()}
def_base={team:weighted_unit_score(profile,DEFENSE_WEIGHTS) for team,profile in profiles.items()}

prior_opponents=defaultdict(list)
for g in current_records:
 if not g.get("result"):continue
 if int(g.get("week") or 0)>=current_week:continue
 home=canon_team(g.get("home"));away=canon_team(g.get("away"))
 if home:prior_opponents[home].append(away)
 if away:prior_opponents[away].append(home)

unit_raw={}
for team in current_board:
 opponents=prior_opponents.get(canon_team(team),[])
 # Offensive performance is scaled by the defensive quality of defenses faced.
 faced_def=[def_base.get(canon_team(o)) for o in opponents if def_base.get(canon_team(o)) is not None]
 # Defensive performance is scaled by the offensive quality of offenses faced.
 faced_off=[off_base.get(canon_team(o)) for o in opponents if off_base.get(canon_team(o)) is not None]
 opp_def=sum(faced_def)/len(faced_def) if faced_def else None
 opp_off=sum(faced_off)/len(faced_off) if faced_off else None
 ob=off_base.get(team)
 db=def_base.get(team)
 unit_raw[team]={
  "offensive_base":round(ob,2) if ob is not None else None,
  "defensive_base":round(db,2) if db is not None else None,
  "opponent_defensive_quality":round(opp_def,2) if opp_def is not None else None,
  "opponent_offensive_quality":round(opp_off,2) if opp_off is not None else None,
  "offensive_multiplier":round(opponent_multiplier(opp_def),3),
  "defensive_multiplier":round(opponent_multiplier(opp_off),3),
  "offensive_adjusted_raw":(ob*opponent_multiplier(opp_def)) if ob is not None else None,
  "defensive_adjusted_raw":(db*opponent_multiplier(opp_off)) if db is not None else None,
 }

off_values=[x["offensive_adjusted_raw"] for x in unit_raw.values() if x["offensive_adjusted_raw"] is not None]
def_values=[x["defensive_adjusted_raw"] for x in unit_raw.values() if x["defensive_adjusted_raw"] is not None]
for team,x in unit_raw.items():
 x["offensive_strength"]=pct_score(x["offensive_adjusted_raw"],off_values) if x["offensive_adjusted_raw"] is not None else None
 x["defensive_strength"]=pct_score(x["defensive_adjusted_raw"],def_values) if x["defensive_adjusted_raw"] is not None else None
 if x["offensive_strength"] is not None and x["defensive_strength"] is not None:
  x["overall_raw"]=0.50*x["offensive_strength"]+0.50*x["defensive_strength"]
 else:
  x["overall_raw"]=None

overall_values=[x["overall_raw"] for x in unit_raw.values() if x["overall_raw"] is not None]
ranked_overall=sorted(
 [t for t,x in unit_raw.items() if x["overall_raw"] is not None],
 key=lambda t:(-unit_raw[t]["overall_raw"],t)
)
overall_rank={team:i for i,team in enumerate(ranked_overall,1)}
off_rank={team:i for i,team in enumerate(sorted([t for t,x in unit_raw.items() if x["offensive_strength"] is not None],key=lambda t:(-unit_raw[t]["offensive_strength"],t)),1)}
def_rank={team:i for i,team in enumerate(sorted([t for t,x in unit_raw.items() if x["defensive_strength"] is not None],key=lambda t:(-unit_raw[t]["defensive_strength"],t)),1)}

current_teams=[]
for team,row in sorted(current_board.items()):
 profile=profiles.get(team)
 units=unit_raw.get(team,{})
 overall_score=pct_score(units.get("overall_raw"),overall_values) if units.get("overall_raw") is not None else row.get("strength_score")
 current_teams.append({
  "team":team,
  **row,
  "advanced":profile,
  "offensive_strength":units.get("offensive_strength"),
  "offensive_strength_rank":off_rank.get(team),
  "defensive_strength":units.get("defensive_strength"),
  "defensive_strength_rank":def_rank.get(team),
  "overall_strength_score":overall_score,
  "overall_strength_rank":overall_rank.get(team) or row.get("national_strength_rank"),
  "opponent_defensive_quality":units.get("opponent_defensive_quality"),
  "opponent_offensive_quality":units.get("opponent_offensive_quality"),
  "offensive_multiplier":units.get("offensive_multiplier"),
  "defensive_multiplier":units.get("defensive_multiplier"),
  "unit_strength_model":"performance_x_opponent_unit_multiplier",
 })
current_teams.sort(key=lambda r:(r.get("overall_strength_rank") or 999,r["team"]))

(DATA/"current_rankings.json").write_text(
 json.dumps({
  "generated_at":now.isoformat(),
  "season":now.year,
  "week":current_week,
  "through_week":max(0,current_week-1),
  "snapshot_type":"current_to_date",
  "model":{
   "offense":"weighted offensive performance × opponent defensive-quality multiplier (0.80x–1.20x)",
   "defense":"weighted defensive performance × opponent offensive-quality multiplier (0.80x–1.20x)",
   "overall":"50% Offensive Strength + 50% Defensive Strength, re-percentiled across FBS",
  },
  "fbs_field_size":len(current_teams),
  "teams":current_teams,
 },indent=2),
 encoding="utf-8",
)
print(f"Published {len(all_upcoming)} upcoming games, {len(current_teams)} opponent-adjusted current FBS strength rows, and historical indexes for {len(strength)} seasons")
