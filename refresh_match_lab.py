#!/usr/bin/env python3
import csv,json,os,time,urllib.parse,urllib.request
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parent; DATA=ROOT/"data"; (DATA/"historical").mkdir(parents=True,exist_ok=True)
KEY=os.environ.get("CFBD_API_KEY")
if not KEY: raise SystemExit("CFBD_API_KEY secret is required")
def api(path,**params):
 url="https://api.collegefootballdata.com"+path+"?"+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"MatchLab/1.0"})
 last_error=None
 for attempt in range(5):
  try:
   with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
  except Exception as exc:
   last_error=exc
   if attempt==4:raise
   time.sleep(2**attempt)
 raise last_error
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
 eligible=[x for x in rankings if int(x.get("week") or 0)<=int(week)]
 snap=max(eligible,key=lambda x:int(x.get("week") or 0),default=None)
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
# Historical matchup snapshots remain pregame-safe. This live board intentionally
# includes every completed game available at build time.
current_week=max(1,last_completed+1)
current_board=live_strength(current_week)

# Game-level opponent-adjusted performance model.
# Each offensive game is graded against a pregame expectation built from the
# offense's prior production and the opponent defense's prior allowance. Defense
# receives the mirror image of the opponent offense's performance-vs-expectation.
# Opponent unit quality then adjusts the magnitude of the over/under-performance.
GAME_COMPONENT_WEIGHTS={
 "ppa":0.45,
 "success_rate":0.20,
 "explosiveness":0.15,
 "finishing":0.10,
 "scoring":0.10,
}
NEUTRAL_UNIT_STRENGTH=50.0
FCS_UNIT_STRENGTH=15.0
RECENCY_STEP=0.05
RECENCY_CAP=1.15

def safe_float(v):
 try:return float(v) if v is not None else None
 except:return None

def mean_or_none(values):
 vals=[float(v) for v in values if v is not None]
 return sum(vals)/len(vals) if vals else None

def std_or_one(values):
 vals=[float(v) for v in values if v is not None]
 if len(vals)<2:return 1.0
 m=sum(vals)/len(vals)
 var=sum((v-m)**2 for v in vals)/(len(vals)-1)
 return max(var**0.5,1e-6)

def pct_rank_desc(values):
 vals=[float(v) for v in values if v is not None]
 out={}
 if len(vals)<2:return out
 ordered=sorted(vals)
 for v in vals:
  below=sum(x<v for x in ordered)
  tied=sum(x==v for x in ordered)
  out[v]=max(1,min(100,int(100*(below+(tied-1)/2)/(len(ordered)-1)+0.5)))
 return out

def game_metric_row(row,points):
 offense=row.get("offense") or {}
 drives=safe_float(offense.get("drives"))
 return {
  "ppa":safe_float(offense.get("ppa")),
  "success_rate":safe_float(offense.get("successRate")),
  "explosiveness":safe_float(offense.get("explosiveness")),
  "finishing":(float(points)/drives) if points is not None and drives and drives>0 else None,
  "scoring":safe_float(points),
 }

# Fetch all current-season game-level advanced rows in one request. CFBD's
# game-advanced endpoint supplies PPA, success rate and explosiveness per team/game.
game_advanced=api(
 "/stats/game/advanced",
 year=now.year,
 seasonType="regular",
 excludeGarbageTime="true",
)
game_results={str(g.get("game_id")):g for g in current_records if g.get("result")}
rows_by_game=defaultdict(dict)
for row in game_advanced:
 gid=str(row.get("gameId"))
 team=canon_team(row.get("team"))
 if gid not in game_results or not team:continue
 rows_by_game[gid][team]=row

# Week-local distributions provide a neutral expectation and normalization scale
# without borrowing information from future weeks.
week_values=defaultdict(lambda:defaultdict(list))
for gid,team_rows in rows_by_game.items():
 g=game_results.get(gid)
 if not g:continue
 week=int(g.get("week") or 0)
 for team,row in team_rows.items():
  result_data=g.get("result") or {}
  points=result_data.get("home_points") if canon_team(g.get("home"))==team else result_data.get("away_points")
  metrics=game_metric_row(row,points)
  for key,value in metrics.items():
   if value is not None:week_values[week][key].append(value)

# Histories contain only games already processed. That means each expectation uses
# what was known before that game rather than end-of-season opponent statistics.
off_history=defaultdict(lambda:defaultdict(list))
def_allowed_history=defaultdict(lambda:defaultdict(list))
off_game_scores=defaultdict(list)
def_game_scores=defaultdict(list)
opponent_def_quality_log=defaultdict(list)
opponent_off_quality_log=defaultdict(list)
off_multiplier_log=defaultdict(list)
def_multiplier_log=defaultdict(list)

# Unit strengths are recomputed after each week and then used as the opponent
# quality reference for the following week's games.
off_strength_entering={team:NEUTRAL_UNIT_STRENGTH for team in current_board}
def_strength_entering={team:NEUTRAL_UNIT_STRENGTH for team in current_board}

def expectation(team,opponent,key,week):
 own=mean_or_none(off_history[team][key])
 opp=mean_or_none(def_allowed_history[opponent][key])
 neutral=mean_or_none(week_values[week][key])
 candidates=[v for v in (own,opp) if v is not None]
 if len(candidates)==2:return 0.5*candidates[0]+0.5*candidates[1]
 if len(candidates)==1 and neutral is not None:return 0.65*candidates[0]+0.35*neutral
 if len(candidates)==1:return candidates[0]
 return neutral

def quality_multiplier(opponent_strength,residual):
 # Positive performances are boosted against stronger units and discounted
 # against weaker units. Negative performances are penalized more against weak
 # units and softened against strong units. Range: 0.80x–1.20x.
 q=(max(0.0,min(100.0,float(opponent_strength)))-50.0)/50.0
 factor=(1.0+0.20*q) if residual>=0 else (1.0-0.20*q)
 return max(0.80,min(1.20,factor))

def season_weighted_average(entries):
 if not entries:return None
 weighted=0.0;weights=0.0
 n=len(entries)
 for i,value in enumerate(entries):
  recency=min(RECENCY_CAP,1.0+RECENCY_STEP*max(0,i))
  weighted+=float(value)*recency
  weights+=recency
 return weighted/weights if weights else None

weeks=sorted({int(g.get("week") or 0) for g in current_records if g.get("result")})
for week in weeks:
 week_games=[
  g for g in current_records
  if g.get("result") and int(g.get("week") or 0)==week
 ]
 pending=[]
 for g in sorted(week_games,key=lambda x:x.get("start_date") or ""):
  gid=str(g.get("game_id"))
  home=canon_team(g.get("home"));away=canon_team(g.get("away"))
  team_rows=rows_by_game.get(gid,{})
  if home not in team_rows or away not in team_rows:continue
  result_data=g.get("result") or {}
  points_map={
   home:result_data.get("home_points"),
   away:result_data.get("away_points"),
  }
  metrics={
   home:game_metric_row(team_rows[home],points_map[home]),
   away:game_metric_row(team_rows[away],points_map[away]),
  }
  for team,opp in ((home,away),(away,home)):
   component_residuals={}
   for key,weight in GAME_COMPONENT_WEIGHTS.items():
    actual=metrics[team].get(key)
    expected=expectation(team,opp,key,week)
    if actual is None or expected is None:continue
    scale=std_or_one(week_values[week][key])
    component_residuals[key]=(actual-expected)/scale
   if not component_residuals:continue
   available_weight=sum(GAME_COMPONENT_WEIGHTS[k] for k in component_residuals)
   weighted_z=sum(component_residuals[k]*GAME_COMPONENT_WEIGHTS[k] for k in component_residuals)/available_weight
   base_score=max(0.0,min(100.0,50.0+15.0*weighted_z))
   opp_def_strength=def_strength_entering.get(opp,FCS_UNIT_STRENGTH)
   mult=quality_multiplier(opp_def_strength,base_score-50.0)
   adjusted=max(0.0,min(100.0,50.0+(base_score-50.0)*mult))
   pending.append((team,opp,metrics[team],metrics[opp],adjusted,mult,opp_def_strength))

 # Record offense and mirrored defense only after every game in the week is graded,
 # so same-week games all use the same entering-strength snapshot.
 for team,opp,team_metrics,opp_metrics,off_score,off_mult,opp_def_strength in pending:
  off_game_scores[team].append(off_score)
  opponent_def_quality_log[team].append(opp_def_strength)
  off_multiplier_log[team].append(off_mult)

  # The opponent defense receives the mirror of this offense's performance score,
  # adjusted by the offense quality it faced entering the week.
  opp_off_strength=off_strength_entering.get(team,FCS_UNIT_STRENGTH)
  defensive_base=100.0-off_score
  defensive_residual=defensive_base-50.0
  def_mult=quality_multiplier(opp_off_strength,defensive_residual)
  defensive_adjusted=max(0.0,min(100.0,50.0+defensive_residual*def_mult))
  def_game_scores[opp].append(defensive_adjusted)
  opponent_off_quality_log[opp].append(opp_off_strength)
  def_multiplier_log[opp].append(def_mult)

  for key,value in team_metrics.items():
   if value is not None:off_history[team][key].append(value)
  # The opponent defense allowed exactly the offensive output generated by team.
  for key,value in team_metrics.items():
   if value is not None:def_allowed_history[opp][key].append(value)

 # Recompute current unit percentiles to become the opponent-quality reference
 # entering the next week.
 off_raw={t:season_weighted_average(off_game_scores[t]) for t in current_board}
 def_raw={t:season_weighted_average(def_game_scores[t]) for t in current_board}
 off_vals=[v for v in off_raw.values() if v is not None]
 def_vals=[v for v in def_raw.values() if v is not None]
 for t in current_board:
  if off_raw[t] is not None:off_strength_entering[t]=pct_score(off_raw[t],off_vals)
  if def_raw[t] is not None:def_strength_entering[t]=pct_score(def_raw[t],def_vals)

unit_raw={}
off_raw={t:season_weighted_average(off_game_scores[t]) for t in current_board}
def_raw={t:season_weighted_average(def_game_scores[t]) for t in current_board}
off_values=[v for v in off_raw.values() if v is not None]
def_values=[v for v in def_raw.values() if v is not None]
for team in current_board:
 offensive_strength=pct_score(off_raw[team],off_values) if off_raw[team] is not None else None
 defensive_strength=pct_score(def_raw[team],def_values) if def_raw[team] is not None else None
 unit_raw[team]={
  "offensive_performance_vs_expectation":round(off_raw[team],2) if off_raw[team] is not None else None,
  "defensive_performance_vs_expectation":round(def_raw[team],2) if def_raw[team] is not None else None,
  "offensive_strength":offensive_strength,
  "defensive_strength":defensive_strength,
  "opponent_defensive_quality":round(mean_or_none(opponent_def_quality_log[team]),2) if opponent_def_quality_log[team] else None,
  "opponent_offensive_quality":round(mean_or_none(opponent_off_quality_log[team]),2) if opponent_off_quality_log[team] else None,
  "offensive_multiplier":round(mean_or_none(off_multiplier_log[team]),3) if off_multiplier_log[team] else None,
  "defensive_multiplier":round(mean_or_none(def_multiplier_log[team]),3) if def_multiplier_log[team] else None,
  "games_modeled":len(off_game_scores[team]),
 }
 if offensive_strength is not None and defensive_strength is not None:
  unit_raw[team]["overall_raw"]=0.50*offensive_strength+0.50*defensive_strength
 else:
  unit_raw[team]["overall_raw"]=None

overall_values=[x["overall_raw"] for x in unit_raw.values() if x["overall_raw"] is not None]
ranked_overall=sorted([t for t,x in unit_raw.items() if x["overall_raw"] is not None],key=lambda t:(-unit_raw[t]["overall_raw"],t))
overall_rank={team:i for i,team in enumerate(ranked_overall,1)}
off_rank={team:i for i,team in enumerate(sorted([t for t,x in unit_raw.items() if x["offensive_strength"] is not None],key=lambda t:(-unit_raw[t]["offensive_strength"],t)),1)}
def_rank={team:i for i,team in enumerate(sorted([t for t,x in unit_raw.items() if x["defensive_strength"] is not None],key=lambda t:(-unit_raw[t]["defensive_strength"],t)),1)}

current_teams=[]
for team,row in sorted(current_board.items()):
 units=unit_raw.get(team,{})
 overall_score=pct_score(units.get("overall_raw"),overall_values) if units.get("overall_raw") is not None else None
 current_teams.append({
  "team":team,
  **row,
  "advanced":adv(now.year,current_week,team),
  "offensive_strength":units.get("offensive_strength"),
  "offensive_strength_rank":off_rank.get(team),
  "defensive_strength":units.get("defensive_strength"),
  "defensive_strength_rank":def_rank.get(team),
  "overall_strength_score":overall_score,
  "overall_strength_rank":overall_rank.get(team),
  "offensive_performance_vs_expectation":units.get("offensive_performance_vs_expectation"),
  "defensive_performance_vs_expectation":units.get("defensive_performance_vs_expectation"),
  "opponent_defensive_quality":units.get("opponent_defensive_quality"),
  "opponent_offensive_quality":units.get("opponent_offensive_quality"),
  "offensive_multiplier":units.get("offensive_multiplier"),
  "defensive_multiplier":units.get("defensive_multiplier"),
  "games_modeled":units.get("games_modeled"),
  "unit_strength_model":"game_level_performance_vs_expectation",
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
   "offense":"45% PPA vs expectation + 20% success rate vs expectation + 15% explosiveness vs expectation + 10% points/drive vs expectation + 10% scoring vs expectation; game deviation adjusted by opponent defensive strength",
   "defense":"mirror of opponent offensive performance vs expectation, adjusted by opponent offensive strength",
   "expectation":"pregame blend of the team's prior production and opponent's prior allowance, with same-week FBS baseline fallback",
   "opponent_adjustment":"asymmetric 0.80x–1.20x adjustment: strong opponents amplify positive outperformance and soften underperformance; weak opponents do the reverse",
   "recency":"5% additional weight per successive game, capped at 1.15x",
   "overall":"50% Offensive Strength + 50% Defensive Strength, re-percentiled across FBS",
   "ap_rank":"reference only; never enters the formula",
  },
  "fbs_field_size":len(current_teams),
  "teams":current_teams,
 },indent=2),
 encoding="utf-8",
)
print(f"Published {len(all_upcoming)} upcoming games, {len(current_teams)} performance-vs-expectation FBS strength rows, and historical indexes for {len(strength)} seasons")

