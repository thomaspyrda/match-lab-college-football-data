#!/usr/bin/env python3
"""Build and run research-only cross-metric recursive composite-opponent hybrid."""
import pathlib, subprocess, sys, os, json
root=pathlib.Path(__file__).resolve().parent
src=(root/'experiment_dominance_v15.py').read_text()
begin=src.index('    off_metric={}; def_metric={}')
end=src.index('    # Persist raw FCS residual diagnostics',begin)
block='''    # HYBRID: all individual metric residuals respond to the SAME recursively
    # updated opponent composite unit SD. Updates are synchronous (Jacobi).
    # FCS evidence remains downside-only, with original preseason fade.
    game_metric={}
    for m in METRICS:
        g=[]
        for h,a,hm,am in obs:
            if hm[m] is not None:g.append((h,a,(hm[m]-mus[m])/sds[m]))
            if am[m] is not None:g.append((a,h,(am[m]-mus[m])/sds[m]))
        game_metric[m]=g
    fcs_off={};fcs_def={}
    for m in METRICS:
        fo=defaultdict(list);fd=defaultdict(list)
        for t,own,opp in fcs_obs:
            if own[m] is not None:
                z=(own[m]-mus[m])/sds[m]
                residual=z-calibration["metrics"].get(m,{}).get("offense_expected_z",-1.5)
                if residual<0:fo[t].append(residual)
            if opp[m] is not None:
                z=(opp[m]-mus[m])/sds[m]
                residual=-z-calibration["metrics"].get(m,{}).get("defense_expected_z",-1.5)
                if residual<0:fd[t].append(residual)
        fcs_off[m]=fo;fcs_def[m]=fd
    # Composite unit seeds are the same FBS-centered preseason priors.
    comp_off={t:prior_z.get(t,0.0) for t in teams}
    comp_def=comp_off.copy()
    convergence={}
    for iteration in range(120):
        off_metric={};def_metric={}
        for m in METRICS:
            by_team=defaultdict(list);faced=defaultdict(list)
            for offense,opponent,z in game_metric[m]:
                by_team[offense].append((opponent,z))
                faced[opponent].append((offense,z))
            sens=mult_calibration["metrics"].get(m,{}).get("selected_coefficient",0.20) * HYBRID_COEFF
            no={};nd={}
            for t in teams:
                evidence=mean([adjusted_evidence(z,comp_def.get(o,0),sens) for o,z in by_team[t]]+fcs_off[m].get(t,[]))
                dev=mean([adjusted_evidence(-z,comp_off.get(o,0),sens) for o,z in faced[t]]+fcs_def[m].get(t,[]))
                pw=evidence_prior_weight(game_counts[t])
                no[t]=pw*prior_z.get(t,0)+(1-pw)*(evidence if evidence is not None else prior_z.get(t,0))
                nd[t]=pw*prior_z.get(t,0)+(1-pw)*(dev if dev is not None else prior_z.get(t,0))
            off_metric[m]=zdict(no);def_metric[m]=zdict(nd)
        next_off=zdict(composite(off_metric,teams))
        next_def=zdict(composite(def_metric,teams))
        # Damping ensures convergence under strong cross-unit feedback.
        next_off=zdict({t:.65*next_off[t]+.35*comp_off[t] for t in teams})
        next_def=zdict({t:.65*next_def[t]+.35*comp_def[t] for t in teams})
        delta=max(max(abs(next_off[t]-comp_off[t]) for t in teams),max(abs(next_def[t]-comp_def[t]) for t in teams))
        comp_off,comp_def=next_off,next_def
        if delta<.001:break
    for m in METRICS:
        convergence[m]={"iterations":iteration+1,"max_delta":round(delta,6)}
    assert delta < .001,f"Hybrid recursive calculation failed convergence: {delta}"
'''
src=src[:begin]+block+src[end:]
src=src.replace('    calibration=json.loads(FCS_CALIBRATION.read_text())','    HYBRID_COEFF=float(os.environ.get("HYBRID_COEFF","1.0"))\n    calibration=json.loads(FCS_CALIBRATION.read_text())')
src=src.replace('OUT=ROOT/"data"/"experiments"/f"recursive_unit_strength_v15_{SEASON}_week_{WEEK}.json"','OUT=ROOT/"data"/"experiments"/f"hybrid_recursive_composite_{os.environ.get(\'HYBRID_LABEL\',\'1p0\')}_{SEASON}_week_{WEEK}.json"')
p=root/'_hybrid_recursive_runtime.py'
p.write_text(src)
try:
 for label,coefficient in [('0p75',.75),('1p0',1.0),('1p25',1.25)]:
  subprocess.run([sys.executable,str(p)],check=True,env=dict(os.environ,MODEL_WEEK='7',HYBRID_LABEL=label,HYBRID_COEFF=str(coefficient)),timeout=720)
finally:p.unlink(missing_ok=True)
base=json.loads((root/'data/experiments/recursive_unit_strength_v15_2026_week_7.json').read_text())['rankings']
baseline={r['team']:r for r in base}
variants=[]
for label,k in [('0p75',.75),('1p0',1.0),('1p25',1.25)]:
 data=json.loads((root/f'data/experiments/hybrid_recursive_composite_{label}_2026_week_7.json').read_text())
 rows=data['rankings'];indexed={r['team']:r for r in rows}
 focus=[]
 for name in ('Miami','Texas Tech','New Mexico','Liberty','Alabama','Georgia','Notre Dame','Utah'):
  r=indexed[name];b=baseline[name]
  focus.append({'team':name,'rank':r['rank'],'v15_rank':b['rank'],'strength_sd':r['overall_team_strength_sd'],'v15_sd':b['overall_team_strength_sd'],'offense_rank':r['offense_rank'],'defense_rank':r['defense_rank']})
 conv=data['convergence']
 variants.append({'coefficient_multiplier':k,'top10':[r['team'] for r in rows[:10]],'focus':focus,'max_iterations':max(v['iterations'] for v in conv.values()),'max_delta':max(v['max_delta'] for v in conv.values())})
report={'model':'hybrid-recursive-composite-v1','fbs_population':len(base),'recursive':True,'method':'Each metric adjusts with corresponding recursively updated opposing composite unit SD, synchronous damped fixed-point iterations. Full v15 metric categories, prior, FCS downside, 50/50 preserved.','limits':'Retrospective week7 ratings through week6; not a pregame predictive backtest. No calibration against future game results yet.','production_unchanged':True,'variants':variants}
(root/'data/experiments/hybrid_recursive_comparison_2026.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
