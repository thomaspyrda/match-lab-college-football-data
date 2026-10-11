#!/usr/bin/env python3
"""Research-only symmetric nonlinear recursive opponent strength sensitivities."""
import pathlib,subprocess,sys,os,json
root=pathlib.Path(__file__).resolve().parent
src=(root/'experiment_dominance_v15.py').read_text()
start=src.index('    off_metric={}; def_metric={}')
end=src.index('    # Persist raw FCS residual diagnostics',start)
block="    # HYBRID: all individual metric residuals respond to the SAME recursively\n    # updated opponent composite unit SD. Updates are synchronous (Jacobi).\n    # FCS evidence remains downside-only, with original preseason fade.\n    game_metric={}\n    for m in METRICS:\n        g=[]\n        for h,a,hm,am in obs:\n            if hm[m] is not None:g.append((h,a,(hm[m]-mus[m])/sds[m]))\n            if am[m] is not None:g.append((a,h,(am[m]-mus[m])/sds[m]))\n        game_metric[m]=g\n    fcs_off={};fcs_def={}\n    for m in METRICS:\n        fo=defaultdict(list);fd=defaultdict(list)\n        for t,own,opp in fcs_obs:\n            if own[m] is not None:\n                z=(own[m]-mus[m])/sds[m]\n                residual=z-calibration[\"metrics\"].get(m,{}).get(\"offense_expected_z\",-1.5)\n                if residual<0:fo[t].append(residual)\n            if opp[m] is not None:\n                z=(opp[m]-mus[m])/sds[m]\n                residual=-z-calibration[\"metrics\"].get(m,{}).get(\"defense_expected_z\",-1.5)\n                if residual<0:fd[t].append(residual)\n        fcs_off[m]=fo;fcs_def[m]=fd\n    # Composite unit seeds are the same FBS-centered preseason priors.\n    comp_off={t:prior_z.get(t,0.0) for t in teams}\n    comp_def=comp_off.copy()\n    convergence={}\n    for iteration in range(120):\n        off_metric={};def_metric={}\n        for m in METRICS:\n            by_team=defaultdict(list);faced=defaultdict(list)\n            for offense,opponent,z in game_metric[m]:\n                by_team[offense].append((opponent,z))\n                faced[opponent].append((offense,z))\n            sens=mult_calibration[\"metrics\"].get(m,{}).get(\"selected_coefficient\",0.20) * HYBRID_COEFF\n            no={};nd={}\n            for t in teams:\n                evidence=mean([adjusted_evidence(z,nonlinear(comp_def.get(o,0)),sens) for o,z in by_team[t]]+fcs_off[m].get(t,[]))\n                dev=mean([adjusted_evidence(-z,nonlinear(comp_off.get(o,0)),sens) for o,z in faced[t]]+fcs_def[m].get(t,[]))\n                pw=evidence_prior_weight(game_counts[t])\n                no[t]=pw*prior_z.get(t,0)+(1-pw)*(evidence if evidence is not None else prior_z.get(t,0))\n                nd[t]=pw*prior_z.get(t,0)+(1-pw)*(dev if dev is not None else prior_z.get(t,0))\n            off_metric[m]=zdict(no);def_metric[m]=zdict(nd)\n        next_off=zdict(composite(off_metric,teams))\n        next_def=zdict(composite(def_metric,teams))\n        # Damping ensures convergence under strong cross-unit feedback.\n        next_off=zdict({t:.65*next_off[t]+.35*comp_off[t] for t in teams})\n        next_def=zdict({t:.65*next_def[t]+.35*comp_def[t] for t in teams})\n        delta=max(max(abs(next_off[t]-comp_off[t]) for t in teams),max(abs(next_def[t]-comp_def[t]) for t in teams))\n        comp_off,comp_def=next_off,next_def\n        if delta<.001:break\n    for m in METRICS:\n        convergence[m]={\"iterations\":iteration+1,\"max_delta\":round(delta,6)}\n    assert delta < .001,f\"Hybrid recursive calculation failed convergence: {delta}\"\n"
assert 'nonlinear(comp_def' in block and 'nonlinear(comp_off' in block
src=src[:start]+block+src[end:]
src=src.replace('    calibration=json.loads(FCS_CALIBRATION.read_text())','    HYBRID_COEFF=1.0\n    CURVE=float(os.environ.get("CURVE","0.0"))\n    def nonlinear(z):\n        v=max(-2.5,min(2.5,z))\n        return v+CURVE*v*v*v\n    calibration=json.loads(FCS_CALIBRATION.read_text())')
needle='OUT=ROOT/"data"/"experiments"/f"recursive_unit_strength_v15_{SEASON}_week_{WEEK}.json"'
assert needle in src
src=src.replace(needle,'OUT=ROOT/"data"/"experiments"/f"hybrid_nonlinear_{os.environ.get(\'CURVE_LABEL\',\'linear\')}_{SEASON}_week_{WEEK}.json"')
p=root/'_research_nonlinear_runtime.py'
p.write_text(src)
labels=[('linear',0.0),('mild',0.05),('moderate',0.10),('strong',0.20)]
try:
 for label,curve in labels:
  subprocess.run([sys.executable,str(p)],env=dict(os.environ,MODEL_WEEK='7',CURVE_LABEL=label,CURVE=str(curve)),check=True,timeout=720)
finally:p.unlink(missing_ok=True)
baseline={r['team']:r for r in json.loads((root/'data/experiments/recursive_unit_strength_v15_2026_week_7.json').read_text())['rankings']}
rows=[]
for label,curve in labels:
 data=json.loads((root/f'data/experiments/hybrid_nonlinear_{label}_2026_week_7.json').read_text())
 ranking=data['rankings'];named={r['team']:r for r in ranking}
 focus=[]
 for team in ('Texas Tech','Miami','Notre Dame','Utah','New Mexico','Liberty','Alabama','Georgia','Ohio State'):
  x=named[team]
  focus.append({'team':team,'rank':x['rank'],'sd':x['overall_team_strength_sd'],'v15_rank':baseline[team]['rank'],'v15_sd':baseline[team]['overall_team_strength_sd']})
 rows.append({'curve':label,'lambda':curve,'top10':[r['team'] for r in ranking[:10]],'focus':focus,'iterations':max(x['iterations'] for x in data['convergence'].values()),'max_delta':max(x['max_delta'] for x in data['convergence'].values())})
result={'model':'recursive hybrid nonlinear opponent adjustment','nonlinear_transform':'z + lambda * clamp(z,-2.5,2.5)^3','note':'Transforms recursively updated opponent composite unit strength for each per-metric adjustment. Not SOS multiplier. Category weights, preseason anchor, FCS policy unchanged.','not_validated':'Retrospective through week 6 only; no independent future-game predictive validation. Do not select model based on rank plausibility alone.','production_unchanged':True,'variants':rows}
(root/'data/experiments/hybrid_nonlinear_comparison_2026.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
