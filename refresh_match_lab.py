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
 completed=[]
 for g in prior:
  r=result(team,g)
  if not r:continue
  home=g.get("homeTeam")==team
  completed.append(r|{
   "opponent":g.get("awayTeam") if home else g.get("homeTeam"),
   "location":"H" if home else "A",
   "week":int(g.get("week") or 0),
  })
 rr=completed
 last5=rr[-5:]
 return {
  "games":len(rr),
  "wins":sum(x["won"] for x in rr),
  "losses":sum(not x["won"] for x in rr),
  "avg_points":round(sum(x["points"] for x in rr)/len(rr),1) if rr else None,
  "avg_allowed":round(sum(x["allowed"] for x in rr)/len(rr),1) if rr else None,
  "coming_off_loss":(not rr[-1]["won"]) if rr else None,
  "last_five":[{
    "week":x["week"],"opponent":x["opponent"],"location":x["location"],
    "result":"W" if x["won"] else "L","points":x["points"],"allowed":x["allowed"]
   } for x in last5],
 }
strength={}
for p in (DATA/"weekly").glob("*.json"):
 d=json.loads(p.read_text());strength[int(d["season"])]=d["weeks"]
preseason_consensus={}
preseason_dir=DATA/"preseason"
if preseason_dir.exists():
 for p in preseason_dir.glob("*.json"):
  d=json.loads(p.read_text())
  preseason_consensus[int(d["season"])]=d
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
 "Ole Miss":"Mississippi",
 "Mississippi":"Mississippi",
 "UTSA":"Texas-San Antonio",
 "Texas-San Antonio":"Texas-San Antonio",
 "Appalachian State":"App State",
 "App State":"App State",
 "FIU":"Florida International",
 "Florida International":"Florida International",
 "San Jose State":"San José State",
 "San José State":"San José State",
}
def canon_team(team):
 return TEAM_ALIASES.get(team,team)

def tier(score):
 if score is None:return None
 s=float(score)
 if s>=95:return "Elite"
 if s>=85:return "Great"
 if s>=76:return "Very Strong"
 if s>=65:return "Strong"
 if s>=50:return "Above Average"
 return "Below Average"

def pct_score(value,values):
 usable=[float(v) for v in values if v is not None]
 if value is None or len(usable)<2:return None
 value=float(value);below=sum(v<value for v in usable);tied=sum(v==value for v in usable)
 return max(1,min(100,int(100*(below+(tied-1)/2)/(len(usable)-1)+0.5)))

def preseason_board(year):
 # Prefer the frozen, source-audited preseason consensus for seasons where one
 # exists. This keeps the starting prior tied to projections for the upcoming
 # season rather than carrying forward the previous season's final results.
 consensus=preseason_consensus.get(year)
 if consensus:
  out={}
  for team,row in (consensus.get("teams") or {}).items():
   score=row.get("score")
   if score is not None:out[canon_team(team)]=float(score)
  if out:return out

 # Historical fallback for seasons that predate the explicit consensus files.
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
  # SOS is a strict national rank among FBS teams: #1 = hardest schedule
  # actually played to date. Keep the continuous value internally for modeling.
  sos_order=sorted((t for t in teams if sos_raw[t] is not None),key=lambda t:(-sos_raw[t],t))
  sos_rank_map={t:i for i,t in enumerate(sos_order,1)}
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
    "schedule_strength_rank":sos_rank_map.get(t),
    "schedule_strength_score":pct_score(sos_raw[t],sos_values) if sos_raw[t] is not None else None,
    "games_in_rating":games_played[t],
    "record":None,
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
 teams=board.get("teams",{})
 r=teams.get(team)
 if r is None:
  key=canon_team(team)
  for name,row in teams.items():
   if canon_team(name)==key:
    r=row
    break
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
 return {canon_team(r.get("school")):int(r["rank"]) for r in (poll or {}).get("ranks",[]) if r.get("school")}
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
 "ppa":0.30,
 "success_rate":0.20,
 "explosiveness":0.15,
 "finishing":0.15,
 "passing_success":0.10,
 "rushing_success":0.10,
}
# Final unit rankings use ranks, not raw metric magnitudes. Each metric is first
# opponent-adjusted game by game, then teams are ranked nationally in that metric.
RANK_METRIC_WEIGHTS={
 "ppa":0.30,
 "success_rate":0.20,
 "explosiveness":0.15,
 "finishing":0.15,
 "passing_success":0.10,
 "rushing_success":0.10,
}
NEUTRAL_UNIT_STRENGTH=50.0
FCS_UNIT_STRENGTH=15.0
RECENCY_STEP=0.05
RECENCY_CAP=1.15
ABSOLUTE_PERFORMANCE_WEIGHT=0.50
EXPECTATION_PERFORMANCE_WEIGHT=0.50
OPPONENT_ADJUSTMENT=0.20
OVERALL_OFFENSE_WEIGHT=0.55
OVERALL_DEFENSE_WEIGHT=0.45
STATISTICAL_GAME_WEIGHT=0.85
RESULT_GAME_WEIGHT=0.15
COMPETITION_ADJUSTMENT=0.25
RESULT_MARGIN_CAP=28.0
UNIT_UPDATE_RATE=0.28
MAX_UNIT_GAME_DELTA=10.0
INTERNAL_RATING_MAX=115.0
BREAKOUT_MAX_BOOST=1.55
QUALITY_WIN_MIN_OPPONENT=75.0
QUALITY_WIN_MAX_BONUS=6.0
VALIDATED_BREAKOUT_MIN_OPPONENT=85.0
VALIDATED_BREAKOUT_MAX_BONUS=8.0
VALIDATED_BREAKOUT_GAME_CAP=14.0

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
 passing=offense.get("passingPlays") or {}
 rushing=offense.get("rushingPlays") or {}
 return {
  "ppa":safe_float(offense.get("ppa")),
  "success_rate":safe_float(offense.get("successRate")),
  "explosiveness":safe_float(offense.get("explosiveness")),
  "finishing":(float(points)/drives) if points is not None and drives and drives>0 else None,
  "passing_success":safe_float(passing.get("successRate")),
  "rushing_success":safe_float(rushing.get("successRate")),
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
off_scoring_percentiles=defaultdict(list)
off_points_log=defaultdict(list)
off_validated_targets=defaultdict(list)
off_rank_metric_grades=defaultdict(lambda:defaultdict(list))
def_rank_metric_grades=defaultdict(lambda:defaultdict(list))

# Offensive and defensive power ratings begin at the real preseason team-strength
# prior and evolve game by game. This preserves preseason information early while
# allowing sustained current-season evidence to take over.
preseason_ratings=preseason_board(now.year)
off_strength_entering={team:preseason_ratings.get(team,NEUTRAL_UNIT_STRENGTH) for team in current_board}
def_strength_entering={team:preseason_ratings.get(team,NEUTRAL_UNIT_STRENGTH) for team in current_board}

def expectation(team,opponent,key,week):
 own=mean_or_none(off_history[team][key])
 opp=mean_or_none(def_allowed_history[opponent][key])
 neutral=mean_or_none(week_values[week][key])
 candidates=[v for v in (own,opp) if v is not None]
 if len(candidates)==2:return 0.5*candidates[0]+0.5*candidates[1]
 if len(candidates)==1 and neutral is not None:return 0.65*candidates[0]+0.35*neutral
 if len(candidates)==1:return candidates[0]
 return neutral

def current_evidence_strength(team,unit="overall"):
 off=off_strength_entering.get(team)
 deff=def_strength_entering.get(team)
 if unit=="offense":return off
 if unit=="defense":return deff
 if off is None and deff is None:return None
 if off is None:return deff
 if deff is None:return off
 return OVERALL_OFFENSE_WEIGHT*float(off)+OVERALL_DEFENSE_WEIGHT*float(deff)

def competition_current_weight(week):
 # Preseason ranking is the competition anchor early, then actual season
 # evidence is allowed to take over gradually.
 if week<=3:return 0.0
 if week==4:return 0.15
 if week==5:return 0.30
 if week==6:return 0.45
 if week==7:return 0.60
 return 0.75

def competition_strength(opponent,week,unit="overall"):
 # Unit-specific opponent quality is critical. An offense is graded against the
 # defense it actually faced; a defense is graded against the offense it faced.
 # The shared preseason prior supplies the early-season talent/competition
 # baseline, then current unit evidence progressively takes over.
 preseason=preseason_ratings.get(opponent,FCS_UNIT_STRENGTH)
 current=current_evidence_strength(opponent,unit)
 if current is None:return preseason
 cw=competition_current_weight(week)
 return (1.0-cw)*float(preseason)+cw*float(current)

def quality_multiplier(opponent_strength,residual):
 # Strong competition amplifies positive performances and softens poor ones.
 # Weak competition does the opposite. Competition is preseason-anchored.
 q=(max(0.0,min(100.0,float(opponent_strength)))-50.0)/50.0
 factor=(1.0+COMPETITION_ADJUSTMENT*q) if residual>=0 else (1.0-COMPETITION_ADJUSTMENT*q)
 return max(0.75,min(1.25,factor))

def result_score(team,opp,is_home,points,opp_points,opp_quality):
 team_quality=current_evidence_strength(team)