#!/usr/bin/env python3
"""Experimental BetWise opponent-adjusted standardized power ratings.

Backend research only. This does not modify current_rankings.json or the public UI.
Uses raw pregame advanced profiles, adjusts each metric for the average quality of
the units faced, standardizes against the FBS population, then builds hierarchical
offense/defense composites to avoid double-counting correlated statistics.
"""
import json, math, statistics
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SEASON=2026
WEEK=6
PROFILE=ROOT/"data"/"profiles"/f"{SEASON}.json"
HISTORY=ROOT/"data"/"historical"/f"{SEASON}.json"
OUT=ROOT/"data"/"experiments"/f"standardized_power_{SEASON}_week_{WEEK}.json"

OFF_CATS={
 "efficiency":(.30,["offensive_efficiency","overall_success"]),
 "passing":(.25,["passing_ppa","passing_success","passing_explosiveness"]),
 "rushing":(.20,["rushing_ppa","rushing_success","line_yards","stuff_rate","power_success","second_level_yards","open_field_yards","rushing_explosiveness"]),
 "situational":(.10,["standard_down_success","passing_down_success"]),
 "finishing":(.15,["finishing_drives"]),
}
DEF_CATS={
 "efficiency":(.30,["defensive_efficiency","defensive_success"]),
 "passing":(.25,["defensive_passing_ppa","defensive_passing_success","defensive_passing_explosiveness"]),
 "rushing":(.20,["defensive_rushing_ppa","defensive_rushing_success","defensive_line_yards","defensive_stuff_rate","defensive_power_success","defensive_second_level_yards","defensive_open_field_yards","defensive_rushing_explosiveness"]),
 "situational":(.10,["defensive_standard_down_success","defensive_passing_down_success","havoc"]),
 "finishing":(.15,["defensive_finishing_drives"]),
}
LOWER_BETTER={
 "defensive_efficiency","defensive_success","defensive_rushing_success","defensive_passing_success",
 "defensive_explosiveness","defensive_finishing_drives","stuff_rate","defensive_standard_down_success",
 "defensive_passing_down_success","defensive_line_yards","defensive_power_success","defensive_second_level_yards",
 "defensive_open_field_yards","defensive_passing_ppa","defensive_rushing_ppa",
 "defensive_passing_explosiveness","defensive_rushing_explosiveness"
}

def standardize(values, lower=False):
    usable=[v for v in values.values() if v is not None]
    if len(usable)<2: return {t:None for t in values}
    mu=statistics.fmean(usable); sd=statistics.pstdev(usable)
    if sd==0: return {t:0.0 if v is not None else None for t,v in values.items()}
    sign=-1 if lower else 1
    return {t:(sign*(v-mu)/sd if v is not None else None) for t,v in values.items()}

def avg(vals):
    vals=[v for v in vals if v is not None]
    return statistics.fmean(vals) if vals else None

def category_scores(metric_z,cats,teams):
    out={}
    for t in teams:
        parts=[]
        for cat,(weight,metrics) in cats.items():
            v=avg([metric_z[m].get(t) for m in metrics])
            if v is not None: parts.append((weight,v))
        denom=sum(w for w,_ in parts)
        out[t]=sum(w*v for w,v in parts)/denom if denom else None
    return out

def main():
    pdata=json.loads(PROFILE.read_text())
    board=pdata["weeks"][str(WEEK)]
    teams=board["teams"]
    raw={t:p.get("raw",{}) for t,p in teams.items()}
    fbs=set(teams)
    games=json.loads(HISTORY.read_text()).get("games",[])
    opponents=defaultdict(list)
    for g in games:
        if not g.get("result") or int(g.get("week") or 0)>=WEEK: continue
        h,a=g.get("home"),g.get("away")
        if h in fbs and a in fbs:
            opponents[h].append(a); opponents[a].append(h)

    metrics=set(m for _,ms in OFF_CATS.values() for m in ms)|set(m for _,ms in DEF_CATS.values() for m in ms)
    raw_z={}
    for m in metrics:
        raw_z[m]=standardize({t:raw[t].get(m) for t in teams},m in LOWER_BETTER)

    # Iterative schedule adjustment. One SD of opponent-unit quality earns one SD
    # of schedule credit before re-standardization. Four passes are enough to stabilize.
    metric_z={m:dict(z) for m,z in raw_z.items()}
    for _ in range(4):
        off=category_scores(metric_z,OFF_CATS,teams)
        deff=category_scores(metric_z,DEF_CATS,teams)
        adjusted={}
        off_metrics={m for _,ms in OFF_CATS.values() for m in ms}
        for m in metrics:
            vals={}
            for t in teams:
                base=raw_z[m].get(t)
                if base is None: vals[t]=None; continue
                oppq=avg([(deff.get(o) if m in off_metrics else off.get(o)) for o in opponents.get(t,[])])
                vals[t]=base+(oppq if oppq is not None else 0.0)
            # Values are already direction-normalized; re-standardize directly.
            usable=[v for v in vals.values() if v is not None]
            mu=statistics.fmean(usable); sd=statistics.pstdev(usable)
            adjusted[m]={t:((v-mu)/sd if v is not None and sd else 0.0 if v is not None else None) for t,v in vals.items()}
        metric_z=adjusted

    off=category_scores(metric_z,OFF_CATS,teams)
    deff=category_scores(metric_z,DEF_CATS,teams)
    overall={t:.55*off[t]+.45*deff[t] for t in teams if off[t] is not None and deff[t] is not None}
    def ranks(vals):
        order=sorted(vals,key=lambda t:vals[t],reverse=True)
        return {t:i+1 for i,t in enumerate(order)}
    orank,drank,trank=ranks(off),ranks(deff),ranks(overall)
    rows=[]
    for t in sorted(overall,key=overall.get,reverse=True):
        rows.append({"team":t,"rank":trank[t],"overall_z":round(overall[t],3),"offense_rank":orank[t],"offense_z":round(off[t],3),"defense_rank":drank[t],"defense_z":round(deff[t],3),"fbs_opponents_count":len(opponents.get(t,[]))})
    payload={"schema_version":"experimental-1.0","season":SEASON,"pregame_week":WEEK,"through_week":board["through_week"],"fbs_field_size":board.get("fbs_field_size"),"public_ui":False,"method":"raw metric -> opponent-unit adjustment -> FBS z-score -> hierarchical category composite","overall_weights":{"offense":.55,"defense":.45},"iterations":4,"rankings":rows}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2)+"\n")
    print("Experimental top 25")
    for r in rows[:25]: print(f'{r["rank"]:>2}. {r["team"]:<22} {r["overall_z"]:+.3f}  O#{r["offense_rank"]:<3} D#{r["defense_rank"]:<3}')

if __name__=="__main__": main()
