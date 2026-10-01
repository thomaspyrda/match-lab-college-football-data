#!/usr/bin/env python3
"""BetWise experimental v2: opponent-expectation unit strength.

Research-only. Never writes current_rankings.json or public UI files.
Each game is graded as actual performance versus an expectation derived from
(1) the team's prior production and (2) the opponent unit's prior allowance.
Weak opponents create easier expectations; meeting/exceeding those expectations
is not punished. PPG and points/play are explicit model inputs.
"""
import json, os, statistics, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SEASON=2026
WEEK=6
HISTORY=ROOT/"data"/"historical"/f"{SEASON}.json"
OUT=ROOT/"data"/"experiments"/f"expected_performance_{SEASON}_week_{WEEK}.json"
KEY=os.environ.get("CFBD_API_KEY")
if not KEY: raise SystemExit("CFBD_API_KEY secret required")

# 16 dimensions. Category weighting prevents clusters of correlated metrics
# (e.g. multiple rushing measures) from overwhelming scoring/efficiency.
CATS={
 "scoring":(.22,["points","points_per_play"]),
 "efficiency":(.23,["ppa","success_rate"]),
 "passing":(.18,["passing_ppa","passing_success","passing_explosiveness"]),
 "rushing":(.17,["rushing_ppa","rushing_success","rushing_explosiveness"]),
 "line":(.10,["line_yards","power_success","second_level_yards","open_field_yards"]),
 "finishing":(.10,["finishing"]),
}
LOWER_OFF={"rushing_explosiveness","passing_explosiveness"}  # CFBD explosiveness is an efficiency cost metric.

def api(path,**params):
    url="https://api.collegefootballdata.com"+path+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"MatchLab/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)

def f(v):
    try:return float(v) if v is not None else None
    except:return None

def mean(vals):
    vals=[float(x) for x in vals if x is not None]
    return statistics.fmean(vals) if vals else None

def zmap(vals):
    usable=[v for v in vals.values() if v is not None]
    if len(usable)<2:return {k:0.0 if v is not None else None for k,v in vals.items()}
    mu=statistics.fmean(usable); sd=statistics.pstdev(usable)
    return {k:((v-mu)/sd if v is not None and sd else 0.0 if v is not None else None) for k,v in vals.items()}

def metric_row(row,points):
    o=row.get("offense") or {}
    p=o.get("passingPlays") or {}; r=o.get("rushingPlays") or {}
    plays=f(o.get("plays")); drives=f(o.get("drives"))
    return {
      "points":f(points),
      "points_per_play":(f(points)/plays if points is not None and plays else None),
      "ppa":f(o.get("ppa")),
      "success_rate":f(o.get("successRate")),
      "passing_ppa":f(p.get("ppa")),
      "passing_success":f(p.get("successRate")),
      "passing_explosiveness":f(p.get("explosiveness")),
      "rushing_ppa":f(r.get("ppa")),
      "rushing_success":f(r.get("successRate")),
      "rushing_explosiveness":f(r.get("explosiveness")),
      "line_yards":f(o.get("lineYards")),
      "power_success":f(o.get("powerSuccess")),
      "second_level_yards":f(o.get("secondLevelYards")),
      "open_field_yards":f(o.get("openFieldYards")),
      "finishing":(f(points)/drives if points is not None and drives else None),
      "explosiveness":f(o.get("explosiveness")),
    }

def expected(own_hist,opp_allowed,key,neutral):
    a=mean(own_hist[key]); b=mean(opp_allowed[key])
    if a is not None and b is not None:return .5*a+.5*b
    if a is not None:return .65*a+.35*neutral if neutral is not None else a
    if b is not None:return .65*b+.35*neutral if neutral is not None else b
    return neutral

def composite(metric_scores,teams):
    out={}
    for t in teams:
        cats=[]
        for _,(w,metrics) in CATS.items():
            vals=[metric_scores[m].get(t) for m in metrics if metric_scores[m].get(t) is not None]
            if vals: cats.append((w,statistics.fmean(vals)))
        den=sum(w for w,_ in cats)
        out[t]=sum(w*v for w,v in cats)/den if den else None
    return out

def main():
    hist=json.loads(HISTORY.read_text())["games"]
    games=[g for g in hist if g.get("result") and int(g.get("week") or 0)<WEEK]
    adv=api("/stats/game/advanced",year=SEASON,seasonType="regular",excludeGarbageTime="true")
    by_gid=defaultdict(dict)
    for row in adv: by_gid[str(row.get("gameId"))][row.get("team")]=row

    # FBS population comes from CFBD's explicit FBS team endpoint, preventing FCS
    # teams from entering the national standard-deviation population.
    fbs_rows=api("/teams/fbs",year=SEASON)
    fbs={x.get("school") for x in fbs_rows if x.get("school")}

    observations=[]
    for g in sorted(games,key=lambda x:(int(x.get("week") or 0),x.get("start_date") or "")):
        gid=str(g.get("game_id")); h=g.get("home"); a=g.get("away"); res=g.get("result") or {}
        if h not in fbs or a not in fbs: continue
        if h not in by_gid.get(gid,{}) or a not in by_gid.get(gid,{}): continue
        observations.append((int(g.get("week") or 0),gid,h,a,
          metric_row(by_gid[gid][h],res.get("home_points")),
          metric_row(by_gid[gid][a],res.get("away_points"))))

    metrics=sorted({m for _,ms in CATS.values() for m in ms})
    # Neutral baselines use only games already played before Week 6.
    neutral={m:mean([row[m] for *_,hm,am in observations for row in (hm,am)]) for m in metrics}
    scale={}
    for m in metrics:
        vals=[row[m] for *_,hm,am in observations for row in (hm,am) if row[m] is not None]
        scale[m]=statistics.pstdev(vals) if len(vals)>1 else 1.0
        if not scale[m]:scale[m]=1.0

    off_hist=defaultdict(lambda:defaultdict(list)); allowed_hist=defaultdict(lambda:defaultdict(list))
    off_grades=defaultdict(lambda:defaultdict(list)); def_grades=defaultdict(lambda:defaultdict(list))
    game_counts=defaultdict(int)

    for week,gid,h,a,hm,am in observations:
        for team,opp,actual,oppactual in ((h,a,hm,am),(a,h,am,hm)):
            game_counts[team]+=1
            for m in metrics:
                x=actual.get(m); ox=oppactual.get(m)
                exp=expected(off_hist[team],allowed_hist[opp],m,neutral[m])
                opp_exp=expected(off_hist[opp],allowed_hist[team],m,neutral[m])
                if x is not None and exp is not None:
                    direction=-1.0 if m in LOWER_OFF else 1.0
                    # 70% performance-vs-expectation, 30% absolute quality.
                    residual=direction*(x-exp)/scale[m]
                    absolute=direction*(x-neutral[m])/scale[m]
                    off_grades[team][m].append(.70*residual+.30*absolute)
                if ox is not None and opp_exp is not None:
                    direction=-1.0 if m in LOWER_OFF else 1.0
                    # Defense is good when opponent production falls below expectation.
                    residual=-direction*(ox-opp_exp)/scale[m]
                    absolute=-direction*(ox-neutral[m])/scale[m]
                    def_grades[team][m].append(.70*residual+.30*absolute)
            for m in metrics:
                if actual.get(m) is not None:off_hist[team][m].append(actual[m])
                if oppactual.get(m) is not None:allowed_hist[team][m].append(oppactual[m])

    teams=sorted(t for t in fbs if game_counts[t]>0)
    off_metric={m:{t:mean(off_grades[t][m]) for t in teams} for m in metrics}
    def_metric={m:{t:mean(def_grades[t][m]) for t in teams} for m in metrics}
    # Re-standardize each adjusted metric across the true FBS population.
    off_z={m:zmap(off_metric[m]) for m in metrics}; def_z={m:zmap(def_metric[m]) for m in metrics}
    off=composite(off_z,teams); deff=composite(def_z,teams)
    overall={t:.50*off[t]+.50*deff[t] for t in teams if off[t] is not None and deff[t] is not None}

    def ranks(vals):
        return {t:i+1 for i,t in enumerate(sorted(vals,key=lambda k:vals[k],reverse=True))}
    ro,rd,rt=ranks(off),ranks(deff),ranks(overall)
    rows=[]
    for t in sorted(overall,key=overall.get,reverse=True):
        rows.append({"team":t,"rank":rt[t],"team_strength_z":round(overall[t],3),
          "offense_rank":ro[t],"offensive_strength_z":round(off[t],3),
          "defense_rank":rd[t],"defensive_strength_z":round(deff[t],3),
          "games":game_counts[t],
          "ppg":round(mean(off_hist[t]["points"]),2) if mean(off_hist[t]["points"]) is not None else None,
          "points_per_play":round(mean(off_hist[t]["points_per_play"]),4) if mean(off_hist[t]["points_per_play"]) is not None else None,
          "ppg_allowed":round(mean(allowed_hist[t]["points"]),2) if mean(allowed_hist[t]["points"]) is not None else None,
          "points_per_play_allowed":round(mean(allowed_hist[t]["points_per_play"]),4) if mean(allowed_hist[t]["points_per_play"]) is not None else None})
    payload={"schema_version":"experimental-2.0","season":SEASON,"pregame_week":WEEK,
      "through_week":WEEK-1,"public_ui":False,"fbs_only":True,"fbs_teams_ranked":len(rows),
      "method":"16-metric game-level performance vs opponent-specific expectation; PPG and points/play explicit; 50/50 offense-defense Team Strength",
      "game_grade_weights":{"performance_vs_expected":.70,"absolute_performance":.30},
      "team_strength_weights":{"offense":.50,"defense":.50},"category_weights":{k:v[0] for k,v in CATS.items()},
      "rankings":rows}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2)+"\n")
    print("Experimental v2 top 25")
    for r in rows[:25]:print(f'{r["rank"]:>2}. {r["team"]:<22} {r["team_strength_z"]:+.3f} O#{r["offense_rank"]:<3} D#{r["defense_rank"]:<3} PPG {r["ppg"]} PA {r["ppg_allowed"]}')

if __name__=="__main__":main()
