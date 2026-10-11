#!/usr/bin/env python3
"""Research-only cumulative competitive evidence, 75/15/10 versus 85/15."""
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
src=src.replace(old,'OUT=ROOT/"data"/"experiments"/f"hybrid_competitive_credit_75_15_10_2026_week_7.json"')
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
    # Cumulative competitive evidence: only performances at or above an
    # opponent-specific competitive threshold may earn positive credit.
    # Pure schedule exposure earns zero; defeat still incurs no automatic bonus.
    # Per-game credit is bounded and game-count exposure uses diminishing returns.
    competitive=defaultdict(list)
    competitive_games=defaultdict(list)
    for t,results in result_games.items():
        for opponent,pf,pa,expected in results:
            opponent_sd=base_overall[opponent]
            # Strong competition gate: 0 SD is average FBS, >0 increasingly strong.
            quality=max(0.0,min(2.5,opponent_sd))
            result=1.0 if pf>pa else .5 if pf==pa else 0.0
            # Measured positive outcome surprise versus opponent; no bonus for
            # mere schedule exposure. Loss may receive only small credit when
            # it is against exceptional competition and remains competitive.
            surprise=result-expected
            margin=(pf-pa)
            close_loss=(result==0 and margin>=-7 and opponent_sd>=1.0)
            earned=max(0.0,surprise)*quality + (0.10*quality if close_loss else 0.0)
            # Weak-loss penalty adds genuinely new downside; do not punish
            # respectable losses to strong opposition simply for losing.
            penalty=max(0.0,-surprise)*max(0.0,-opponent_sd)*0.30
            value=min(2.0,earned)-min(0.75,penalty)
            competitive[t].append(value)
            competitive_games[t].append({"opponent":opponent,"own_points":pf,"opp_points":pa,"opponent_sd":round(opponent_sd,3),"credit":round(value,4)})
    # Sum accumulated eligible achievements with diminishing gains and
    # four-game denominator to reduce early-season volatility.
    csc_raw={t:(sum(competitive[t]) / (4+len(competitive[t])) if competitive[t] else 0.0) for t in teams}
    csc=zdict(csc_raw)
    overall=zdict({t:0.75*base_overall[t]+0.15*qrr[t]+0.10*csc[t] for t in teams})
    csc_details={t:{"raw":round(csc_raw[t],5),"sd":round(csc[t],4),"games":competitive_games[t]} for t in teams}
    qrr_details={t:{"games":len(residuals[t]),"wins":sum(1 for x in result_games[t] if x[1]>x[2]),"losses":sum(1 for x in result_games[t] if x[1]<x[2]),"raw_result_surprise":round(raw_qrr[t],5),"qrr_sd":round(qrr[t],4),"baseline_rank":ranks(base_overall)[t],"baseline_sd":round(base_overall[t],4)} for t in teams}
'''
src=src.replace(needle,addition+needle)
src=src.replace('"convergence":convergence,"fcs_diagnostics":fcs_diagnostics,"rankings":rows}', '"convergence":convergence,"fcs_diagnostics":fcs_diagnostics,"competitive_strength_credit":{"weight":0.10,"method":"Accumulated positive strength-adjusted result surprise versus above-average opponents; extra 10% of opponent SD for losses <=7 against opponents >=+1 SD; weak-opponent upset loss penalty; divided by games+4; cross-FBS standardized","details":csc_details},"quality_results":{"weight":QRR_WEIGHT,"definition":"Opponent-strength-adjusted W/L residual over baseline hybrid expected result with 4-game reliability shrinkage; baseline logistic slope 1.2 is a sensitivity assumption, not validated","diagnostics":qrr_details},"rankings":rows}')
tmp=root/'_competitive_credit_runtime.py'
tmp.write_text(src)
try:
 subprocess.run([sys.executable,str(tmp)],check=True,env=dict(os.environ,MODEL_WEEK='7'),timeout=800)
finally:tmp.unlink(missing_ok=True)
new=json.loads((root/'data/experiments/hybrid_competitive_credit_75_15_10_2026_week_7.json').read_text())
base=json.loads((root/'data/experiments/hybrid_quality_results_extreme_15pct_2026_week_7.json').read_text())
old={r['team']:r for r in base['rankings']}
nr={r['team']:r for r in new['rankings']}
dd=new['competitive_strength_credit']['details']
focus=['Kentucky','Georgia','Miami','Notre Dame','Utah','Alabama','Texas Tech','LSU','Texas A&M','South Carolina']
report={'experiment':'75/15/10 cumulative competitive credit vs 85/15 previous','season':2026,'through_week':6,'production_unchanged':True,'method':new['competitive_strength_credit']['method'],'caveats':['Experimental strength threshold and credits have not been calibrated.','Close-loss credits rely on final margin only, not a half-game performance profile.','Opponent strengths are retrospectively estimated using completed games through Week 6.','Some correlation remains with quality results.'],'prior_top25':[{'rank':r['rank'],'team':r['team']} for r in base['rankings'][:25]],'new_top25':[{'rank':r['rank'],'team':r['team'],'old_rank':old[r['team']]['rank'],'change':old[r['team']]['rank']-r['rank'],'sd':r['overall_team_strength_sd'],'csc_sd':dd[r['team']]['sd']} for r in new['rankings'][:25]],'focus':[{'team':t,'old_rank':old[t]['rank'],'new_rank':nr[t]['rank'],'csc_sd':dd[t]['sd'],'games':dd[t]['games']} for t in focus if t in nr]}
(root/'data/experiments/competitive_credit_comparison_2026.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
