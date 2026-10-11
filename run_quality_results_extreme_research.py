#!/usr/bin/env python3
"""Research-only opponent-strength-amplified quality results at 15% and 20%."""
import json,os,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parent
baseline_script=(root/'run_hybrid_recursive_research.py').read_text()
v15=(root/'experiment_dominance_v15.py').read_text()
start=v15.index('    off_metric={}; def_metric={}')
end=v15.index('    # Persist raw FCS residual diagnostics',start)
block=baseline_script.split("block='''",1)[1].split("'''\nsrc=src[:begin]",1)[0]
src=v15[:start]+block+v15[end:]
src=src.replace('    calibration=json.loads(FCS_CALIBRATION.read_text())','    HYBRID_COEFF=1.0\n    QRR_WEIGHT=float(os.environ.get("QRR_WEIGHT","0.15"))\n    calibration=json.loads(FCS_CALIBRATION.read_text())')
old='OUT=ROOT/"data"/"experiments"/f"recursive_unit_strength_v15_{SEASON}_week_{WEEK}.json"'
assert old in src
src=src.replace(old,'OUT=ROOT/"data"/"experiments"/f"hybrid_quality_results_extreme_{os.environ.get(\'QRR_LABEL\',\'15\')}pct_2026_week_7.json"')
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
    overall=zdict({t:(1-QRR_WEIGHT)*base_overall[t]+QRR_WEIGHT*qrr[t] for t in teams})
    qrr_details={t:{"games":len(residuals[t]),"wins":sum(1 for x in result_games[t] if x[1]>x[2]),"losses":sum(1 for x in result_games[t] if x[1]<x[2]),"raw_result_surprise":round(raw_qrr[t],5),"qrr_sd":round(qrr[t],4),"baseline_rank":ranks(base_overall)[t],"baseline_sd":round(base_overall[t],4)} for t in teams}
'''
src=src.replace(needle,addition+needle)
src=src.replace('"convergence":convergence,"fcs_diagnostics":fcs_diagnostics,"rankings":rows}', '"convergence":convergence,"fcs_diagnostics":fcs_diagnostics,"quality_results":{"weight":QRR_WEIGHT,"definition":"Opponent-strength-adjusted W/L residual over baseline hybrid expected result with 4-game reliability shrinkage; baseline logistic slope 1.2 is a sensitivity assumption, not validated","diagnostics":qrr_details},"rankings":rows}')
tmp=root/'_hybrid_quality_extreme_runtime.py'
tmp.write_text(src)
try:
 for label,weight in [('15',.15),('20',.20)]:
  subprocess.run([sys.executable,str(tmp)],env=dict(os.environ,MODEL_WEEK='7',QRR_LABEL=label,QRR_WEIGHT=str(weight)),check=True,timeout=800)
finally:tmp.unlink(missing_ok=True)
prior=json.loads((root/'data/experiments/hybrid_quality_results_10pct_2026_week_7.json').read_text())['rankings']
prior_by={r['team']:r for r in prior}
variants=[]
for label,weight in [('15',.15),('20',.20)]:
 data=json.loads((root/f'data/experiments/hybrid_quality_results_extreme_{label}pct_2026_week_7.json').read_text())
 ranking=data['rankings'];diagnostics=data['quality_results']['diagnostics']
 variants.append({'weight':weight,'top25':[{'rank':r['rank'],'team':r['team'],'old_10pct_rank':prior_by[r['team']]['rank'],'delta_positions':prior_by[r['team']]['rank']-r['rank'],'strength_sd':r['overall_team_strength_sd'],'qrr_sd':diagnostics[r['team']]['qrr_sd']} for r in ranking[:25]],'focus':[{'team':t,'rank':next(r['rank'] for r in ranking if r['team']==t),'old_10pct_rank':prior_by[t]['rank'],'qrr_sd':diagnostics[t]['qrr_sd']} for t in ('Georgia','Alabama','Miami','Utah','Notre Dame','Texas Tech','Liberty','New Mexico')]})
report={'model':'opponent-strength-amplified-quality-results','as_of_week':7,'through_week':6,'baseline':'linear recursive hybrid 90/10 quality residual','specification':'New result residual uses outcome-dependent exponential multiplier 0.35 times opponent composite SD, bounded 0.50 to 2.50. More weight for wins versus strong teams and losses versus weak teams. Same baseline expected outcome; 4-game shrinkage.','caveats':['Prototype coefficients are not calibrated.','Result-based metric can double-count performance; amplification may increase that risk.','No separate schedule-reliability adjustment has yet been applied.'],'old_10pct_top25':[{'rank':r['rank'],'team':r['team'],'sd':r['overall_team_strength_sd']} for r in prior[:25]],'variants':variants,'production_unchanged':True}
(root/'data/experiments/quality_results_extreme_comparison_2026.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
