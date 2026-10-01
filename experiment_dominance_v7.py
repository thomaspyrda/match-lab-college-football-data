#!/usr/bin/env python3
"""BetWise experimental v7: recursive FBS strength with historically calibrated FCS evidence (test-only).

Research only. Never writes current_rankings.json or public UI files. Calibration remains experimental. Historical FCS calibration is generated before this experiment.
Offenses are solved against opposing defenses; defenses against opposing offenses.
All component ratings live in FBS standard-deviation space. A generic preseason
full-FBS prior anchors Week 1 and decays as current-season evidence accumulates.
"""
import json, os, statistics, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SEASON=2026
WEEK=int(os.environ.get("MODEL_WEEK","6"))
HISTORY=ROOT/"data"/"historical"/f"{SEASON}.json"
PRESEASON=ROOT/"data"/"preseason"/f"{SEASON}.json"
OUT=ROOT/"data"/"experiments"/f"recursive_unit_strength_v7_{SEASON}_week_{WEEK}.json"
CALIBRATION=ROOT/"data"/"experiments"/"fcs_metric_calibration_2022_2025.json"
KEY=os.environ.get("CFBD_API_KEY")
if not KEY: raise SystemExit("CFBD_API_KEY secret required")

# Evidence-based preseason prior. Only qualifying FBS games reduce uncertainty;
# byes, FCS games, and unusable profiles do not artificially decay the anchor.
PRIOR_BY_GAMES={0:1.00,1:.75,2:.55,3:.40,4:.20,5:.05,6:0.00}
def evidence_prior_weight(games):
    return PRIOR_BY_GAMES.get(games,0.00)

CATS={
 "scoring":(.22,["points","points_per_play"]),
 "efficiency":(.23,["ppa","success_rate"]),
 "passing":(.18,["passing_ppa","passing_success","passing_explosiveness"]),
 "rushing":(.17,["rushing_ppa","rushing_success","rushing_explosiveness"]),
 "line":(.10,["line_yards","power_success","second_level_yards","open_field_yards"]),
 "finishing":(.10,["finishing"]),
}
METRICS=sorted({m for _,ms in CATS.values() for m in ms})
ALIASES={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
# 2026 transition/classification guardrail. The experiment models the established
# FBS population used by Match Lab; transition/FCS classifications cannot silently
# enter the standardization universe even if an upstream endpoint changes.
FBS_EXCLUSIONS_2026={"Sacramento State","North Dakota State"}
# Synthetic opponent strength used only for downside-only FCS residuals.
# -1.50 SD represents a clearly sub-FBS opponent without admitting FCS teams into the recursive network.
FCS_BASELINE_SD=-1.50

def canon(t): return ALIASES.get(t,t)
def api(path,**params):
    url="https://api.collegefootballdata.com"+path+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"MatchLab/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)
def f(v):
    try:return float(v) if v is not None else None
    except:return None
def mean(v):
    v=[float(x) for x in v if x is not None]
    return statistics.fmean(v) if v else None
def zdict(vals):
    usable=[v for v in vals.values() if v is not None]
    mu=statistics.fmean(usable); sd=statistics.pstdev(usable) if len(usable)>1 else 1
    return {k:((v-mu)/sd if v is not None and sd else None) for k,v in vals.items()}
def metric_row(row,points):
    o=row.get("offense") or {}; p=o.get("passingPlays") or {}; r=o.get("rushingPlays") or {}
    plays=f(o.get("plays")); drives=f(o.get("drives"))
    return {"points":f(points),"points_per_play":(f(points)/plays if points is not None and plays else None),
      "ppa":f(o.get("ppa")),"success_rate":f(o.get("successRate")),
      "passing_ppa":f(p.get("ppa")),"passing_success":f(p.get("successRate")),"passing_explosiveness":f(p.get("explosiveness")),
      "rushing_ppa":f(r.get("ppa")),"rushing_success":f(r.get("successRate")),"rushing_explosiveness":f(r.get("explosiveness")),
      "line_yards":f(o.get("lineYards")),"power_success":f(o.get("powerSuccess")),
      "second_level_yards":f(o.get("secondLevelYards")),"open_field_yards":f(o.get("openFieldYards")),
      "finishing":(f(points)/drives if points is not None and drives else None)}
def composite(metric_ratings,teams):
    out={}
    for t in teams:
        parts=[]
        for _,(w,ms) in CATS.items():
            vals=[metric_ratings[m].get(t) for m in ms if metric_ratings[m].get(t) is not None]
            if vals:parts.append((w,statistics.fmean(vals)))
        den=sum(w for w,_ in parts); out[t]=sum(w*v for w,v in parts)/den if den else None
    return out
def ranks(vals):
    return {t:i+1 for i,t in enumerate(sorted(vals,key=lambda x:vals[x],reverse=True))}

def main():
    calibration=json.loads(CALIBRATION.read_text())
    hist=json.loads(HISTORY.read_text())["games"]
    games=[g for g in hist if g.get("result") and int(g.get("week") or 0)<WEEK]
    adv=api("/stats/game/advanced",year=SEASON,seasonType="regular",excludeGarbageTime="true")
    by_gid=defaultdict(dict)
    for row in adv:
        if row.get("team"):by_gid[str(row.get("gameId"))][canon(row["team"])]=row

    fbs_api={canon(x["school"]) for x in api("/teams/fbs",year=SEASON) if x.get("school")}
    excluded_from_fbs=sorted(t for t in FBS_EXCLUSIONS_2026 if t in fbs_api)
    fbs=fbs_api-FBS_EXCLUSIONS_2026
    preseason=json.loads(PRESEASON.read_text()).get("teams",{})
    prior_raw={canon(t):f(v.get("score")) for t,v in preseason.items() if canon(t) in fbs}
    # Missing preseason entries get the FBS mean, never zero/bottom.
    pm=mean(prior_raw.values())
    prior_z=zdict({t:prior_raw.get(t,pm) for t in fbs})

    obs=[]; fcs_obs=[]
    raw_metric_values=defaultdict(list)
    points_for=defaultdict(list); points_against=defaultdict(list); ppp_for=defaultdict(list); ppp_against=defaultdict(list)
    game_counts=defaultdict(int); fcs_game_counts=defaultdict(int)
    for g in sorted(games,key=lambda x:(int(x.get("week") or 0),x.get("start_date") or "")):
        gid=str(g.get("game_id")); h=canon(g.get("home")); a=canon(g.get("away")); res=g.get("result") or {}
        rows=by_gid.get(gid,{})
        if h not in rows or a not in rows:continue
        hm=metric_row(rows[h],res.get("home_points")); am=metric_row(rows[a],res.get("away_points"))
        h_fbs=h in fbs; a_fbs=a in fbs
        if h_fbs and a_fbs:
            obs.append((h,a,hm,am))
            for row in (hm,am):
                for m in METRICS:
                    if row[m] is not None:raw_metric_values[m].append(row[m])
            for t,own,opp in ((h,hm,am),(a,am,hm)):
                game_counts[t]+=1; points_for[t].append(own["points"]);points_against[t].append(opp["points"])
                ppp_for[t].append(own["points_per_play"]);ppp_against[t].append(opp["points_per_play"])
        elif h_fbs != a_fbs:
            # Preserve the FBS team's actual game metrics, but never admit the FCS team
            # into the recursive population or the preseason-decay game count.
            t,own,opp=(h,hm,am) if h_fbs else (a,am,hm)
            fcs_obs.append((t,own,opp))
            fcs_game_counts[t]+=1

    # Convert every game metric to FBS game-distribution SD units first.
    mus={m:mean(raw_metric_values[m]) for m in METRICS}
    sds={m:(statistics.pstdev(raw_metric_values[m]) if len(raw_metric_values[m])>1 else 1.0) for m in METRICS}
    for m in METRICS:
        if not sds[m]:sds[m]=1.0

    teams=sorted(t for t in fbs if game_counts[t]>0)
    off_metric={}; def_metric={}
    convergence={}
    # Fixed-point solve per metric:
    # observed_z ~= offense_strength - defense_strength.
    # Therefore offense = mean(observed_z + opponent defense), while
    # defense = mean(-observed_z + opponent offense). Both are then shrunk
    # toward the same generic preseason prior according to the weekly decay.
    for m in METRICS:
        games_m=[]
        for h,a,hm,am in obs:
            if hm[m] is not None:games_m.append((h,a,(hm[m]-mus[m])/sds[m]))
            if am[m] is not None:games_m.append((a,h,(am[m]-mus[m])/sds[m]))
        off={t:prior_z.get(t,0.0) for t in teams}; deff={t:prior_z.get(t,0.0) for t in teams}
        by_team=defaultdict(list)
        for t,o,z in games_m:by_team[t].append((o,z))
        # FCS evidence is asymmetric: meeting/exceeding the fixed FCS expectation
        # contributes nothing; only underperformance enters the unit estimate.
        fcs_off_penalty=defaultdict(list); fcs_def_penalty=defaultdict(list)
        for t,own,opp in fcs_obs:
            if own[m] is not None:
                z=(own[m]-mus[m])/sds[m]
                residual=z-calibration["metrics"][m]["offense_expected_z"]
                if residual<0:fcs_off_penalty[t].append(residual)
            if opp[m] is not None:
                z=(opp[m]-mus[m])/sds[m]
                residual=-z-calibration["metrics"][m]["defense_expected_z"]
                if residual<0:fcs_def_penalty[t].append(residual)
        delta=None
        for iteration in range(200):
            no={}; nd={}
            for t in teams:
                rows=by_team.get(t,[])
                evidence=mean([z+deff.get(o,0.0) for o,z in rows]+fcs_off_penalty.get(t,[]))
                pw=evidence_prior_weight(game_counts[t])
                no[t]=pw*prior_z.get(t,0.0)+(1-pw)*(evidence if evidence is not None else prior_z.get(t,0.0))
                # Defense evidence comes from every opponent offensive observation against t.
                faced=[(opp,z) for offense,opp,z in games_m if opp==t]
                dev=mean([-z+off.get(offense,0.0) for offense,z in faced]+fcs_def_penalty.get(t,[]))
                pw=evidence_prior_weight(game_counts[t])
                nd[t]=pw*prior_z.get(t,0.0)+(1-pw)*(dev if dev is not None else prior_z.get(t,0.0))
            # Center and scale each unit back to FBS SD space every pass.
            no=zdict(no); nd=zdict(nd)
            delta=max(max(abs(no[t]-off[t]) for t in teams),max(abs(nd[t]-deff[t]) for t in teams))
            off,deff=no,nd
            if delta<0.001:break
        off_metric[m]=off;def_metric[m]=deff
        convergence[m]={"iterations":iteration+1,"max_delta":round(delta,6)}

    # Persist raw FCS residual diagnostics so the synthetic baseline can be calibrated
    # independently of final ranks and the faster preseason-decay curve.
    fcs_diagnostics=[]
    for t,own,opp in fcs_obs:
        item={"team":t,"metrics":{}}
        for m in METRICS:
            oz=((own[m]-mus[m])/sds[m]) if own[m] is not None else None
            dz=((-((opp[m]-mus[m])/sds[m]))) if opp[m] is not None else None
            oraw=(oz+FCS_BASELINE_SD) if oz is not None else None
            draw=(dz+FCS_BASELINE_SD) if dz is not None else None
            item["metrics"][m]={
                "offense_observed_z":round(oz,4) if oz is not None else None,
                "offense_raw_residual":round(oraw,4) if oraw is not None else None,
                "offense_applied":round(min(0.0,oraw),4) if oraw is not None else None,
                "defense_observed_z":round(dz,4) if dz is not None else None,
                "defense_raw_residual":round(draw,4) if draw is not None else None,
                "defense_applied":round(min(0.0,draw),4) if draw is not None else None}
        fcs_diagnostics.append(item)

    # Diagnostics expose the formula rather than changing it.
    category_off={}; category_def={}
    for cat,(_,ms) in CATS.items():
        category_off[cat]={t:mean([off_metric[m].get(t) for m in ms]) for t in teams}
        category_def[cat]={t:mean([def_metric[m].get(t) for m in ms]) for t in teams}
    off=composite(off_metric,teams);deff=composite(def_metric,teams)
    # Final composites are standardized once more so +1 means one FBS SD.
    off=zdict(off);deff=zdict(deff)
    overall={t:.5*off[t]+.5*deff[t] for t in teams}
    # Standardize the combined rating too: Overall Team Strength is expressed
    # directly in SDs from the FBS mean, while remaining exactly 50/50 O/D.
    overall=zdict(overall)
    ro,rd,rt=ranks(off),ranks(deff),ranks(overall)
    rows=[]
    for t in sorted(teams,key=lambda x:overall[x],reverse=True):
        rows.append({"team":t,"rank":rt[t],"overall_team_strength_sd":round(overall[t],3),
          "offense_rank":ro[t],"offensive_strength_sd":round(off[t],3),
          "defense_rank":rd[t],"defensive_strength_sd":round(deff[t],3),
          "games":game_counts[t],"fcs_games":fcs_game_counts[t],"preseason_weight":evidence_prior_weight(game_counts[t]),"preseason_rank":next((v.get("consensus_rank") for n,v in preseason.items() if canon(n)==t),None),
          "ppg":round(mean(points_for[t]),2),"points_per_play":round(mean(ppp_for[t]),4),
          "ppg_allowed":round(mean(points_against[t]),2),"points_per_play_allowed":round(mean(ppp_against[t]),4),
          "diagnostics":{"offense_categories":{k:round(category_off[k][t],3) for k in CATS},
            "defense_categories":{k:round(category_def[k][t],3) for k in CATS},
            "offense_metrics":{m:round(off_metric[m][t],3) for m in METRICS},
            "defense_metrics":{m:round(def_metric[m][t],3) for m in METRICS}}})
    payload={"schema_version":"experimental-7.0","season":SEASON,"pregame_week":WEEK,"through_week":WEEK-1,
      "public_ui":False,"fbs_only":True,"fbs_teams_ranked":len(rows),
      "population_validation":{"api_fbs_count":len(fbs_api),"model_fbs_count":len(fbs),
        "explicit_exclusions":sorted(FBS_EXCLUSIONS_2026),"excluded_present_in_api":excluded_from_fbs,
        "model_teams_with_games":len(teams)},"preseason_prior_decay":"qualifying_fbs_games","fcs_policy":{"calibration_file":str(CALIBRATION.relative_to(ROOT)),"training_seasons":calibration["training_seasons"],"metric_specific_median_expectations":True,"positive_effect_cap":0.0,"negative_residuals_only":True,"counts_toward_preseason_decay":False}, "preseason_prior_curve":PRIOR_BY_GAMES,
      "method":"recursive fixed-point unit model: game metric standardized across FBS; offense solved vs opponent defense; defense solved vs opponent offense; generic preseason prior decays by qualifying FBS games played; FCS games add downside-only residuals against metric-specific historical FBS-vs-FCS median expectations and never reduce prior weight; 50/50 unit combination",
      "team_strength_weights":{"offense":.5,"defense":.5},"category_weights":{k:v[0] for k,v in CATS.items()},
      "convergence":convergence,"fcs_diagnostics":fcs_diagnostics,"rankings":rows}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2)+"\n")
    print("Experimental v7 calibrated-FCS recursive top 25")
    for r in rows[:25]:print(f'{r["rank"]:>2}. {r["team"]:<22} {r["overall_team_strength_sd"]:+.3f} SD  O#{r["offense_rank"]:<3} D#{r["defense_rank"]:<3}')

if __name__=="__main__":main()
