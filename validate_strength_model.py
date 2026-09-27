#!/usr/bin/env python3
"""Backtest CFB unit-strength calibration against future game results.

This script is intentionally separate from the production builder. It fetches
historical game-level advanced stats, rebuilds ratings chronologically with no
future leakage, tests a small calibration grid, and writes a machine-readable
report that can be used to tune the live model.
"""
import json, math, os, time, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data"
OUT=ROOT/"validation"
OUT.mkdir(exist_ok=True)
KEY=os.environ.get("CFBD_API_KEY")
if not KEY:
    raise SystemExit("CFBD_API_KEY secret is required")

YEARS=(2023,2024,2025)
MIN_PRIOR_GAMES=2
COMPONENT_WEIGHTS={
    "ppa":0.45,
    "success_rate":0.20,
    "explosiveness":0.15,
    "finishing":0.10,
    "scoring":0.10,
}
ABSOLUTE_WEIGHTS=(0.50,0.60,0.70,0.80,0.90)
OPPONENT_ADJUSTMENTS=(0.10,0.15,0.20)
OFFENSE_SHARES=(0.45,0.50,0.55)
RECENCY_STEP=0.05
RECENCY_CAP=1.15

def api(path,**params):
    url="https://api.collegefootballdata.com"+path+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"MatchLabValidation/1.0"})
    last=None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req,timeout=120) as response:
                return json.load(response)
        except Exception as exc:
            last=exc
            if attempt==4: raise
            time.sleep(2**attempt)
    raise last

def canon(team):
    return "Connecticut" if team in ("UConn","Connecticut") else team

def f(v):
    try:return float(v) if v is not None else None
    except:return None

def mean(values):
    vals=[float(v) for v in values if v is not None]
    return sum(vals)/len(vals) if vals else None

def stdev(values):
    vals=[float(v) for v in values if v is not None]
    if len(vals)<2:return 1.0
    m=sum(vals)/len(vals)
    return max((sum((x-m)**2 for x in vals)/(len(vals)-1))**0.5,1e-6)

def percentile(v,values,higher=True):
    vals=[float(x) for x in values if x is not None]
    if v is None or len(vals)<2:return None
    v=float(v)
    worse=sum(x<v for x in vals) if higher else sum(x>v for x in vals)
    tied=sum(x==v for x in vals)
    return max(1,min(100,100*(worse+(tied-1)/2)/(len(vals)-1)))

def corr(xs,ys):
    if len(xs)<3:return None
    mx=sum(xs)/len(xs);my=sum(ys)/len(ys)
    num=sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    dx=sum((x-mx)**2 for x in xs);dy=sum((y-my)**2 for y in ys)
    return num/math.sqrt(dx*dy) if dx>0 and dy>0 else None

def weighted_average(values):
    if not values:return None
    total=0.0;den=0.0
    for i,v in enumerate(values):
        w=min(RECENCY_CAP,1.0+RECENCY_STEP*i)
        total+=v*w;den+=w
    return total/den if den else None

def metric_row(row,points):
    off=row.get("offense") or {}
    drives=f(off.get("drives"))
    return {
        "ppa":f(off.get("ppa")),
        "success_rate":f(off.get("successRate")),
        "explosiveness":f(off.get("explosiveness")),
        "finishing":float(points)/drives if points is not None and drives and drives>0 else None,
        "scoring":f(points),
    }

def load_games(year):
    p=DATA/"historical"/f"{year}.json"
    if not p.exists():return []
    return json.loads(p.read_text(encoding="utf-8")).get("games",[])

def build_year_rows(year):
    games=load_games(year)
    completed={str(g.get("game_id")):g for g in games if g.get("result")}
    advanced=api("/stats/game/advanced",year=year,seasonType="regular",excludeGarbageTime="true")
    by_game=defaultdict(dict)
    for row in advanced:
        gid=str(row.get("gameId"));team=canon(row.get("team"))
        if gid in completed and team:
            by_game[gid][team]=row
    week_values=defaultdict(lambda:defaultdict(list))
    normalized={}
    for gid,g in completed.items():
        rows=by_game.get(gid,{})
        home=canon(g.get("home"));away=canon(g.get("away"))
        if home not in rows or away not in rows:continue
        result=g.get("result") or {}
        m={}
        for team,pts in ((home,result.get("home_points")),(away,result.get("away_points"))):
            m[team]=metric_row(rows[team],pts)
            for key,val in m[team].items():
                if val is not None:week_values[int(g.get("week") or 0)][key].append(val)
        normalized[gid]=(g,home,away,m)
    return normalized,week_values

def evaluate_config(year_data,absolute_weight,opp_adjust,off_share):
    eval_diffs=[];margins=[];correct=0;total=0
    per_year={}
    for year,(normalized,week_values) in year_data.items():
        off_hist=defaultdict(lambda:defaultdict(list))
        def_allowed=defaultdict(lambda:defaultdict(list))
        off_scores=defaultdict(list);def_scores=defaultdict(list)
        off_strength=defaultdict(lambda:50.0);def_strength=defaultdict(lambda:50.0)
        games_played=defaultdict(int)
        ydiff=[];ymargin=[];ycorrect=0;ytotal=0

        weeks=sorted({int(g.get("week") or 0) for g,_,_,_ in normalized.values()})
        for week in weeks:
            # Evaluate future result from ratings that existed before this week.
            week_games=sorted(
                [v for v in normalized.values() if int(v[0].get("week") or 0)==week],
                key=lambda v:v[0].get("start_date") or ""
            )
            pending=[]
            for g,home,away,metrics in week_games:
                if games_played[home]>=MIN_PRIOR_GAMES and games_played[away]>=MIN_PRIOR_GAMES:
                    team_h=off_share*off_strength[home]+(1-off_share)*def_strength[home]
                    team_a=off_share*off_strength[away]+(1-off_share)*def_strength[away]
                    diff=team_h-team_a
                    result=g.get("result") or {}
                    margin=float(result.get("home_points"))-float(result.get("away_points"))
                    ydiff.append(diff);ymargin.append(margin)
                    ytotal+=1
                    if (diff>0 and margin>0) or (diff<0 and margin<0):
                        ycorrect+=1

                for team,opp in ((home,away),(away,home)):
                    component_abs={};component_res={}
                    for key,w in COMPONENT_WEIGHTS.items():
                        actual=metrics[team].get(key)
                        if actual is None:continue
                        vals=week_values[week][key]
                        p=percentile(actual,vals,True)
                        if p is not None:component_abs[key]=p
                        own=mean(off_hist[team][key]);opp_allow=mean(def_allowed[opp][key]);neutral=mean(vals)
                        candidates=[x for x in (own,opp_allow) if x is not None]
                        if len(candidates)==2:expected=0.5*candidates[0]+0.5*candidates[1]
                        elif len(candidates)==1 and neutral is not None:expected=0.65*candidates[0]+0.35*neutral
                        elif len(candidates)==1:expected=candidates[0]
                        else:expected=neutral
                        if expected is not None:
                            component_res[key]=(actual-expected)/stdev(vals)
                    if not component_abs or not component_res:continue
                    wa=sum(COMPONENT_WEIGHTS[k] for k in component_abs)
                    wr=sum(COMPONENT_WEIGHTS[k] for k in component_res)
                    absolute=sum(component_abs[k]*COMPONENT_WEIGHTS[k] for k in component_abs)/wa
                    z=sum(component_res[k]*COMPONENT_WEIGHTS[k] for k in component_res)/wr
                    residual=max(0.0,min(100.0,50.0+15.0*z))
                    q=(max(0,min(100,def_strength[opp]))-50)/50
                    factor=(1+opp_adjust*q) if residual>=50 else (1-opp_adjust*q)
                    residual=max(0.0,min(100.0,50+(residual-50)*factor))
                    game_score=absolute_weight*absolute+(1-absolute_weight)*residual
                    pending.append((team,opp,metrics[team],game_score))

            # Apply only after all same-week games are graded.
            for team,opp,metrics_team,game_score in pending:
                off_scores[team].append(game_score)
                # Defense gets mirror of opponent offensive score, but keeps its own
                # strength baseline through the season.
                def_scores[opp].append(100-game_score)
                for key,val in metrics_team.items():
                    if val is not None:
                        off_hist[team][key].append(val)
                        def_allowed[opp][key].append(val)
                games_played[team]+=1

            teams=set(off_scores)|set(def_scores)
            off_raw={t:weighted_average(off_scores[t]) for t in teams}
            def_raw={t:weighted_average(def_scores[t]) for t in teams}
            ov=[v for v in off_raw.values() if v is not None]
            dv=[v for v in def_raw.values() if v is not None]
            for t in teams:
                if off_raw[t] is not None:off_strength[t]=percentile(off_raw[t],ov,True) or 50
                if def_raw[t] is not None:def_strength[t]=percentile(def_raw[t],dv,True) or 50

        eval_diffs.extend(ydiff);margins.extend(ymargin);correct+=ycorrect;total+=ytotal
        per_year[str(year)]={"games":ytotal,"winner_accuracy":round(ycorrect/ytotal,4) if ytotal else None,"margin_correlation":round(corr(ydiff,ymargin),4) if corr(ydiff,ymargin) is not None else None}

    c=corr(eval_diffs,margins)
    return {
        "absolute_weight":absolute_weight,
        "expectation_weight":round(1-absolute_weight,2),
        "opponent_adjustment":opp_adjust,
        "offense_share":off_share,
        "defense_share":round(1-off_share,2),
        "games":total,
        "winner_accuracy":correct/total if total else 0,
        "margin_correlation":c or 0,
        "per_year":per_year,
    }

def main():
    year_data={}
    for year in YEARS:
        print(f"Loading {year}...")
        year_data[year]=build_year_rows(year)
    results=[]
    for aw in ABSOLUTE_WEIGHTS:
        for oa in OPPONENT_ADJUSTMENTS:
            for os_ in OFFENSE_SHARES:
                results.append(evaluate_config(year_data,aw,oa,os_))
    # Primary objective: predictive margin correlation; winner accuracy breaks ties.
    results.sort(key=lambda r:(r["margin_correlation"],r["winner_accuracy"]),reverse=True)
    best=results[0]
    report={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "seasons":list(YEARS),
        "minimum_prior_games":MIN_PRIOR_GAMES,
        "component_weights":COMPONENT_WEIGHTS,
        "objective":"maximize correlation between pregame Team Strength differential and subsequent scoring margin; winner accuracy used as tiebreaker",
        "best":best,
        "top_10":results[:10],
        "tested_configs":len(results),
    }
    path=OUT/"strength_model_report.json"
    path.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
