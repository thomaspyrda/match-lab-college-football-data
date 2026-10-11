#!/usr/bin/env python3
"""Symmetric game-level performance/outcome interaction, research only."""
import json,os,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parent
baseline_script=(root/'run_hybrid_recursive_research.py').read_text()
v15=(root/'experiment_dominance_v15.py').read_text()
start=v15.index('    off_metric={}; def_metric={}')
end=v15.index('    # Persist raw FCS residual diagnostics',start)
block=baseline_script.split("block='''",1)[1].split("'''\nsrc=src[:begin]",1)[0]
src=v15[:start]+block+v15[end:]
src=src.replace('    calibration=json.loads(FCS_CALIBRATION.read_text())','    HYBRID_COEFF=1.0\n    QRR_WEIGHT=0.15\n    calibration=json.loads(FCS_CALIBRATION.read_text())')
old='OUT=ROOT/"data"/"experiments"/f"recursive_unit_strength_v15_{SEASON}_week_{WEEK}.json"'
assert old in src
src=src.replace(old,'OUT=ROOT/"data"/"experiments"/f"hybrid_symmetric_csc_75_15_10_2026_week_7.json"')
needle='    ro,rd,rt=ranks(off),ranks(deff),ranks(overall)'
assert needle in src
addition='''    # Quality result: actual W/D/L minus expectation implied by existing
    # opponent-adjusted team strength, averaged by team (no margin duplication).
    # Cross-sectional distribution is centered and stabilized with reliability shrinkage.
    import math
    base_overall=overall.copy()
    residuals=defaultdict(list)
    result_games=defaultdict(list)
    for g in games:
        home=canon(g.get("home"));away=canon(g.get("away"))
        if home not in overall or away not in overall:continue
        result=g.get("result") or {}
        hp=result.get("home_points");ap=result.get("away_points")
        if hp is None or ap is None:continue
        hp=float(hp);ap=float(ap)
        actual=1.0 if hp>ap else .5 if hp==ap else 0.0
        # Opponent quality enters via the opposing team's established hybrid strength.
        ex=1/(1+math.exp(-1.2*(base_overall[home]-base_overall[away])))
        # Opponent strength determines significance symmetrically: stronger
        # opponent => greater evidence for a win and for a loss; a weak
        # opponent => smaller win credit but greater penalty for a loss.
        # Opponent strength in FBS SD, bounded multiplicative effect.
        h_opp=max(-2.5,min(2.5,base_overall[away]))
        a_opp=max(-2.5,min(2.5,base_overall[home]))
        h_factor=max(.50,min(2.50,math.exp(.35*h_opp))) if actual>=.5 else max(.50,min(2.50,math.exp(-.35*h_opp)))
        a_factor=max(.50,min(2.50,math.exp(.35*a_opp))) if actual<=.5 else max(.50,min(2.50,math.exp(-.35*a_opp)))
        residuals[home].append((actual-ex)*h_factor)
        residuals[away].append(((1-actual)-(1-ex))*a_factor)
        result_games[home].append((away,hp,ap,round(ex,4)))
        result_games[away].append((home,ap,hp,round(1-ex,4)))
    raw_qrr={t:(sum(residuals[t])/(len(residuals[t])+4) if residuals[t] else 0.0) for t in teams}
    qrr=zdict(raw_qrr)
    # Symmetric performance + result interaction: compare per-game metric
    # evidence to the FBS-adjusted expected performance against each unit.
    # Positive or negative extremes have identical strength scaling and caps.
    metric_signal=defaultdict(list)
    for h,a,hm,am in obs:
        for t,o,own in ((h,a,hm),(a,h,am)):
            terms=[]
            for m in METRICS:
                if own[m] is None:continue
                z=(own[m]-mus[m])/sds[m]
                opponent_def=comp_def.get(o,0.0)
                sens=mult_calibration["metrics"].get(m,{}).get("selected_coefficient",0.20)
                adj=adjusted_evidence(z,opponent_def,sens)
                terms.append(adj)
            if terms:
                metric_signal[(t,o)]=sum(terms)/len(terms)
    competitive=defaultdict(list);competitive_games=defaultdict(list)
    for t,results in result_games.items():
        for opponent,pf,pa,expected in results:
            # Signed quality axis for symmetric positive/negative evidence.
            # A stronger opponent raises the reward for overachievement; a
            # weaker opponent raises the penalty for underachievement.
            opp_sd=max(-2.5,min(2.5,base_overall[opponent]))
            result=(1.0 if pf>pa else .5 if pf==pa else 0.0)
            surprise=result-expected
            perf=metric_signal.get((t,opponent),0.0)
            # Explicit mirror: strength S, statistical signal P and result R
            # have equal/opposite effect under (S,P,R)->(-S,-P,-R).
            # Merely facing a difficult opponent earns nothing.
            p=math.tanh(perf)
            strong=max(0.0,opp_sd)
            weak=max(0.0,-opp_sd)
            pos_performance=strong*max(0.0,p)
            neg_performance=weak*max(0.0,-p)
            pos_result=strong*max(0.0,surprise)
            neg_result=weak*max(0.0,-surprise)
            pos_interaction=strong*max(0.0,p)*max(0.0,surprise)
            neg_interaction=weak*max(0.0,-p)*max(0.0,-surprise)
            value=0.40*((pos_performance-neg_performance)+(pos_result-neg_result)+(pos_interaction-neg_interaction))
            value=max(-2.0,min(2.0,value))
            competitive[t].append(value)
            competitive_games[t].append({"opponent":opponent,"own_points":pf,"opp_points":pa,"opponent_sd":round(opp_sd,3),"performance_signal":round(perf,4),"result_surprise":round(surprise,4),"credit":round(value,4)})
    csc_raw={t:(sum(competitive[t])/(len(competitive[t])+4) if competitive[t] else 0.0) for t in teams}
    csc=zdict(csc_raw)
    overall=zdict({t:.75*base_overall[t]+.15*qrr[t]+.10*csc[t] for t in teams})
    csc_details={t:{"raw":round(csc_raw[t],5),"sd":round(csc[t],4),"games":competitive_games[t]} for t in teams}
    qrr_details={t:{"games":len(residuals[t]),"wins":sum(1 for x in result_games[t] if x[1]>x[2]),"losses":sum(1 for x in result_games[t] if x[1]<x[2]),"raw_result_surprise":round(raw_qrr[t],5),"qrr_sd":round(qrr[t],4),"baseline_rank":ranks(base_overall)[t],"baseline_sd":round(base_overall[t],4)} for t in teams}
'''
src=src.replace(needle,addition+needle)
src=src.replace('"convergence":convergence,"fcs_diagnostics":fcs_diagnostics,"rankings":rows}', '"convergence":convergence,"fcs_diagnostics":fcs_diagnostics,"competitive_strength_credit":{"weight":0.10,"method":"Symmetric outcome and metric-performance interaction with equal positive and negative bounded adjustments; FBS centered","details":csc_details},"quality_results":{"weight":QRR_WEIGHT,"definition":"Opponent-strength-adjusted W/L residual over baseline hybrid expected result with 4-game reliability shrinkage; baseline logistic slope 1.2 is a sensitivity assumption, not validated","diagnostics":qrr_details},"rankings":rows}')
tmp=root/'_symmetric_csc_runtime.py'
tmp.write_text(src)
try:
 subprocess.run([sys.executable,str(tmp)],check=True,env=dict(os.environ,MODEL_WEEK='7'),timeout=800)
finally:tmp.unlink(missing_ok=True)
new=json.loads((root/'data/experiments/hybrid_symmetric_csc_75_15_10_2026_week_7.json').read_text())
old=json.loads((root/'data/experiments/hybrid_competitive_credit_75_15_10_2026_week_7.json').read_text())
old_r={r['team']:r for r in old['rankings']}
d=new['competitive_strength_credit']['details']
focus=['Kentucky','Georgia','Miami','Utah','Texas Tech','Alabama','LSU']
report={'model':'symmetric-competitive-achievement-75-15-10','production_unchanged':True,'through_week':6,'notes':['Prototype uncalibrated symmetric performance/results interaction','Performance signal is unweighted mean of available observed adjusted metrics, not final season composite','Game results and performance signals intentionally both count'],'top25':[{'rank':r['rank'],'team':r['team'],'old_rank':old_r[r['team']]['rank'],'change':old_r[r['team']]['rank']-r['rank'],'sd':r['overall_team_strength_sd'],'csc_sd':d[r['team']]['sd']} for r in new['rankings'][:25]],'focus':[{'team':t,'old_rank':old_r[t]['rank'],'new_rank':next(r['rank'] for r in new['rankings'] if r['team']==t),'csc_sd':d[t]['sd'],'games':d[t]['games']} for t in focus]}
(root/'data/experiments/symmetric_competitive_comparison_2026.json').write_text(json.dumps(report,indent=2)+chr(10))
print(json.dumps(report,indent=2))
