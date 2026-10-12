#!/usr/bin/env python3
"""Research-only weekly four-unit experiment. Requires build_research_archive.py output."""
import csv,json,math,statistics
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FOLDER=ROOT/"data"/"research"/"2026"
rows=list(csv.DictReader((FOLDER/"weekly_team_metrics.csv").open()))
pre=json.loads((FOLDER/"preseason_anchors.json").read_text()).get("teams",{})
# Align CFBD source school names with the preseason consensus before ranking.
ALIASES={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
def canon(x):return ALIASES.get(x,x)
pre={canon(k):v for k,v in pre.items()}
for row in rows:
    row["team"]=canon(row["team"]);row["opponent"]=canon(row["opponent"])
dct=json.loads((FOLDER/"metric_dictionary.json").read_text())
cats=dct["categories"]
# Retain v15 subcategory selection; identify passing/rushing-specific measures,
# and use overall efficiency/scoring/line/finishing in both unit composites at lower weight.
passing=cats["passing"][1]
rushing=cats["rushing"][1]
shared=cats["scoring"][1]+cats["efficiency"][1]+cats["line"][1]+cats["finishing"][1]
teams=sorted({r["team"] for r in rows})
weeks=sorted({int(r["week"]) for r in rows})
byweek=defaultdict(list)
for r in rows:byweek[int(r["week"])].append(r)
def num(v):
    try:return float(v) if v not in ("",None) else None
    except:return None
def zscores(scores):
    vals=list(scores.values());mu=statistics.fmean(vals);sd=statistics.pstdev(vals) or 1
    return {t:(v-mu)/sd for t,v in scores.items()}
initial={t:num(pre.get(t,{}).get("score")) for t in teams}
meanprior=statistics.fmean(v for v in initial.values() if v is not None)
prior=zscores({t:(initial[t] if initial[t] is not None else meanprior) for t in teams})
ANCHOR={0:1.,1:.75,2:.55,3:.40,4:.20,5:.05}
def anchor(n):return ANCHOR.get(min(n,6),0)
# Performance is standardized by metric against the entire FBS game-level
# population before averaging into four units. No future observations in normalization.
def perweek_metric_z(seen):
    metricmap={}
    for side in ("off","def"):
        for m in dct["metric_names"]:
            values=[num(r[side+"_"+m]) for r in seen]
            values=[v for v in values if v is not None]
            if len(values)<10:continue
            mu=statistics.fmean(values);sd=statistics.pstdev(values) or 1.
            metricmap[(side,m)]=(mu,sd)
    return metricmap
def unit_measure(row,kind,scales):
    side="off" if kind in ("PO","RO") else "def"
    names=passing if kind in ("PO","PD") else rushing
    # 80% sport-specific + 20% common metrics; separate category coverage
    def avg(names):
        vals=[]
        for m in names:
            v=num(row.get(side+"_"+m))
            if v is not None and (side,m) in scales:
                mu,sd=scales[(side,m)]
                x=(v-mu)/sd
                if side=="def":x=-x  # allowed values; lower is better
                vals.append(x)
        return statistics.fmean(vals) if vals else None
    a,b=avg(names),avg(shared)
    if a is None:return b
    if b is None:return a
    return .8*a+.2*b
def run(amplitude,qor=False,method="rank",results_heavy=False,weights=(.50,.35,.15)):
    evidence=defaultdict(list)
    frozen={t:{k:prior[t] for k in ("PO","RO","PD","RD")} for t in teams}
    allthrough=[]
    priorcounts=defaultdict(int)
    outcomes=defaultdict(list)
    confidence=defaultdict(list)
    for week in weeks:
        data=byweek[week]
        # Year-to-date baseline is recalibrated using only previously completed games.
        # Rank snapshots for a given week are frozen before consuming that week's data.
        ordered={}
        for k in ("PO","RO","PD","RD"):
            ordered[k]=sorted(teams,key=lambda t:(-frozen[t][k],t))
        n=len(teams)
        order=sorted(teams,key=lambda t:(-statistics.fmean(frozen[t].values()),t))
        pregame_rank={t:i+1 for i,t in enumerate(order)}
        coef={}
        for k in ordered:
            for i,t in enumerate(ordered[k]):
                coef[k,t]=1+amplitude*(1-2*i/max(1,n-1))
        seen=allthrough+data
        scales=perweek_metric_z(seen)
        # Quality of results uses frozen overall strengths, symmetrical actual vs expected margin.
        for r in data:
            t,opp=r["team"],r["opponent"]
            if opp not in frozen:continue
            f=frozen[t];o=frozen[opp]
            match={"PO":"PD","RO":"RD","PD":"PO","RD":"RO"}
            for k in match:
                raw=unit_measure(r,k,scales)
                if raw is None:continue
                # Gap model: additive frozen opponent-unit SD adjustment. Strong defense
                # raises credit for offensive output; weak defense reduces it.
                # Opposite units map similarly on defense. Never adjust via a
                # multiplier on signed performance (wrong direction for negatives).
                if method=="gap":
                    opponent_gap=max(-2.,min(2.,o[match[k]]))
                    adjusted=raw+amplitude*opponent_gap
                elif method=="hybrid":
                    opponent_gap=max(-2.,min(2.,o[match[k]]))
                    rank_adjusted=raw*coef[match[k],opp]
                    gap_adjusted=raw+amplitude*opponent_gap
                    adjusted=.5*rank_adjusted+.5*gap_adjusted
                else:
                    adjusted=raw*coef[match[k],opp]
                evidence[t,k].append((adjusted,max(1,num(r.get("plays_count")) or 1)))
            tp,op=num(r["team_points"]),num(r["opponent_points"])
            if tp is not None and op is not None:
                expected=7*(statistics.fmean(f.values())-statistics.fmean(o.values()))
                resid=max(-35,min(35,(tp-op)-expected))/35
                evidence[t,"result"].append((resid,1))
                if results_heavy:
                    win=int(tp>op)
                    rank=pregame_rank[opp]
                    tier=max(0.,(11-rank)/10) if rank<=10 else 0.
                    outcomes[t].append((1 if win else -1)+.4*resid+.6*tier*win)
                    confidence[t].append(max(0.,min(2.,statistics.fmean(o.values())))*(1 if win else max(0.,resid)))
            if int(r["fbs_opponent"]):priorcounts[t]+=1
        allthrough.extend(data)
        new={}
        for t in teams:
            new[t]={}
            for k in ("PO","RO","PD","RD"):
                a=evidence[t,k]
                empirical=sum(v*w for v,w in a)/sum(w for _,w in a) if a else prior[t]
                weight=anchor(priorcounts[t])
                new[t][k]=weight*prior[t]+(1-weight)*empirical
        # Standardize current unit ratings for comparability next week.
        for k in ("PO","RO","PD","RD"):
            zs=zscores({t:new[t][k] for t in teams})
            for t in teams:new[t][k]=zs[t]
        frozen=new
    if results_heavy:
        strength_z=zscores({t:statistics.fmean(frozen[t].values()) for t in teams})
        outcomes_z=zscores({t:statistics.fmean(outcomes[t]) if outcomes[t] else -1 for t in teams})
        confidence_z=zscores({t:statistics.fmean(confidence[t]) if confidence[t] else 0 for t in teams})
    results=[]
    for t in teams:
        strength=statistics.fmean(frozen[t].values())
        q=evidence[t,"result"]
        quality=sum(v for v,_ in q)/len(q) if q else 0
        score=(weights[0]*strength_z[t]+weights[1]*outcomes_z[t]+weights[2]*confidence_z[t] if results_heavy else strength+(.10*quality if qor else 0))
        results.append({"team":t,"score":round(score,5),"statistical_strength":round(strength,5),
                        "quality_results":round(quality,5),"games":priorcounts[t],
                        **{k:round(frozen[t][k],5) for k in ("PO","RO","PD","RD")}})
    results.sort(key=lambda r:(-r["score"],r["team"]))
    for i,row in enumerate(results,1):row["rank"]=i
    return results
def main():
    if not rows:raise SystemExit("Empty archive")
    variants={"unadjusted":(0,False),"adjust_50":(.5,False),"adjust_65":(.65,False),
              "adjust_50_qor":(.5,True),"adjust_65_qor":(.65,True),
              "unit_gap_50_qor":(.5,True,"gap"),"unit_gap_65_qor":(.65,True,"gap"),
              "hybrid_50_qor":(.5,True,"hybrid"),"hybrid_65_qor":(.65,True,"hybrid"),
              "results_heavy_hybrid_50":(.5,False,"hybrid",True),
              "balanced_hybrid_50":(.5,False,"hybrid",True,(.60,.25,.15)),
              "conservative_hybrid_50":(.5,False,"hybrid",True,(.70,.20,.10))}
    full={key:run(*params) for key,params in variants.items()}
    (FOLDER/"ranking_experiments.json").write_text(json.dumps({"season":2026,"through_week":max(weeks),
       "note":"Experimental four-unit model. Unit-specific 80% and shared 20% aggregation; frozen weekly coefficients.",
       "variants":full},indent=2))
    with (FOLDER/"top25_comparison.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["model","rank","team","score","PO","RO","PD","RD","quality_results"])
        for name,ranking in full.items():
            for r in ranking[:25]:
                w.writerow([name,r["rank"],r["team"],r["score"],r["PO"],r["RO"],r["PD"],r["RD"],r["quality_results"]])
    watch=["Georgia","Miami","Notre Dame","Ohio State","BYU","Alabama","Indiana","Utah",
           "Kentucky","Texas","Florida","Oregon"]
    with (FOLDER/"opponent_gap_watchlist.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["team","model","rank","score","PO","RO","PD","RD","fbs_games"])
        for team in watch:
            for model,rankings in full.items():
                row=next((r for r in rankings if r["team"]==team),None)
                if row:w.writerow([team,model,row["rank"],row["score"],row["PO"],row["RO"],row["PD"],row["RD"],row["games"]])
    for name,ranking in full.items():
        print(name,[(r["rank"],r["team"]) for r in ranking[:12]])
if __name__=="__main__":main()
