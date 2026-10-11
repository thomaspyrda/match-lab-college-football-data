#!/usr/bin/env python3
"""Research-only 10% quality-results residual against recursive-hybrid strength."""
import json,os,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parent
baseline_script=(root/'run_hybrid_recursive_research.py').read_text()
v15=(root/'experiment_dominance_v15.py').read_text()
start=v15.index('    off_metric={}; def_metric={}')
end=v15.index('    # Persist raw FCS residual diagnostics',start)
block=baseline_script.split("block='''",1)[1].split("'''\nsrc=src[:begin]",1)[0]
src=v15[:start]+block+v15[end:]
src=src.replace('    calibration=json.loads(FCS_CALIBRATION.read_text())','    HYBRID_COEFF=1.0\n    calibration=json.loads(FCS_CALIBRATION.read_text())')
old='OUT=ROOT/"data"/"experiments"/f"recursive_unit_strength_v15_{SEASON}_week_{WEEK}.json"'
assert old in src
src=src.replace(old,'OUT=ROOT/"data"/"experiments"/"hybrid_quality_results_10pct_2026_week_7.json"')
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
        residuals[home].append(actual-ex)
        residuals[away].append((1-actual)-(1-ex))
        result_games[home].append((away,hp,ap,round(ex,4)))
        result_games[away].append((home,ap,hp,round(1-ex,4)))
    raw_qrr={t:(sum(residuals[t])/(len(residuals[t])+4) if residuals[t] else 0.0) for t in teams}
    qrr=zdict(raw_qrr)
    overall=zdict({t:.90*base_overall[t]+.10*qrr[t] for t in teams})
    qrr_details={t:{"games":len(residuals[t]),"wins":sum(1 for x in result_games[t] if x[1]>x[2]),"losses":sum(1 for x in result_games[t] if x[1]<x[2]),"raw_result_surprise":round(raw_qrr[t],5),"qrr_sd":round(qrr[t],4),"baseline_rank":ranks(base_overall)[t],"baseline_sd":round(base_overall[t],4)} for t in teams}
'''
src=src.replace(needle,addition+needle)
src=src.replace('"convergence":convergence,"fcs_diagnostics":fcs_diagnostics,"rankings":rows}', '"convergence":convergence,"fcs_diagnostics":fcs_diagnostics,"quality_results":{"weight":0.10,"definition":"Opponent-strength-adjusted W/L residual over baseline hybrid expected result with 4-game reliability shrinkage; baseline logistic slope 1.2 is a sensitivity assumption, not validated","diagnostics":qrr_details},"rankings":rows}')
tmp=root/'_hybrid_quality_results_runtime.py'
tmp.write_text(src)
try:subprocess.run([sys.executable,str(tmp)],env=dict(os.environ,MODEL_WEEK='7'),check=True,timeout=800)
finally:tmp.unlink(missing_ok=True)
data=json.loads((root/'data/experiments/hybrid_quality_results_10pct_2026_week_7.json').read_text())
rows=data['rankings'];details=data['quality_results']['diagnostics']
baseline_ranks={team:d['baseline_rank'] for team,d in details.items()}
report={'model':'hybrid-quality-results-10pct','scope':'2026 completed games through week 6','production_unchanged':True,'description':'90% original linear recursive hybrid strength, 10% opponent-quality-adjusted win-loss surprise rating. Actual result minus expected based on opponent-adjusted baseline strength. No margin repeated. 4-game reliability shrinkage.','caveats':['1.2 logistic slope and 4-game shrink are provisional, not empirically calibrated.','Current-season fitted strengths are used for same-season opponent qualities; descriptive retrospective metric, not pregame predictions.','Result residuals and statistical strength remain correlated.'],'top15':[{'rank':r['rank'],'team':r['team'],'strength_sd':r['overall_team_strength_sd'],'hybrid_rank':baseline_ranks[r['team']],'qrr_sd':details[r['team']]['qrr_sd'],'wins':details[r['team']]['wins'],'losses':details[r['team']]['losses']} for r in rows[:15]],'focus':[{ 'team':t,'rank':next(r['rank'] for r in rows if r['team']==t),**details[t]} for t in ('Miami','Notre Dame','Utah','Texas Tech','New Mexico','Liberty')]}
(root/'data/experiments/hybrid_quality_results_comparison_2026.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
