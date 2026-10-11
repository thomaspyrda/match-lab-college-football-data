#!/usr/bin/env python3
"""NFL-v9-inspired ridge joint offense/defense opponent adjustments, CFB research only."""
import json,os,subprocess,sys,pathlib
root=pathlib.Path(__file__).resolve().parent
original=(root/'experiment_dominance_v15.py').read_text()
start=original.index('    off_metric={}; def_metric={}')
end=original.index('    # Persist raw FCS residual diagnostics',start)
replacement='''    # Joint, regularized FBS network solve: observed game metric = offense effect
    # minus opponent defensive strength; a ridge prior prevents sparse-network
    # extremes. FCS downside is folded in as one-sided regularized evidence.
    import numpy as np
    idx={t:i for i,t in enumerate(teams)}
    n=len(teams)
    off_metric={};def_metric={};convergence={}
    for m in METRICS:
        observations=[]
        for h,a,hm,am in obs:
            if hm[m] is not None:observations.append((h,a,(hm[m]-mus[m])/sds[m]))
            if am[m] is not None:observations.append((a,h,(am[m]-mus[m])/sds[m]))
        # Each observation involves one offense and the opposing defense.
        # Defensive strength is higher-is-better, so design coefficient is -1.
        # A game-normalized metric is one observation. NFL fits play-weighted
        # observations; this prototype is game weighted.
        X=np.zeros((len(observations),2*n+1))
        y=np.zeros(len(observations))
        for j,(offense,defense,z) in enumerate(observations):
            X[j,idx[offense]]=1
            X[j,n+idx[defense]]=-1
            X[j,-1]=1
            y[j]=z
        # Preseason means decline by completed FBS games.
        initial=np.array([prior_z.get(t,0.0) for t in teams]*2+[0.0])
        lam=np.array([RIDGE/(max(0.2,1-evidence_prior_weight(game_counts[t]))) for t in teams]*2+[0.0])
        H=X.T@X+np.diag(lam)
        rhs=X.T@y+lam*initial
        # FCS: below-expectation residual only, never an upside contribution.
        for t,own,opp in fcs_obs:
            if t not in idx:continue
            ix=idx[t]
            for side,raw,key in ((0,own[m],"offense_expected_z"),(1,opp[m],"defense_expected_z")):
                if raw is None:continue
                z=(raw-mus[m])/sds[m]
                observed=z if side==0 else -z
                expected=calibration["metrics"].get(m,{}).get(key,-1.5)
                residual=min(0.0,observed-expected)
                if residual<0:
                    k=ix+side*n
                    H[k,k]+=1.0
                    rhs[k]+=initial[k]+residual
        solved=np.linalg.solve(H,rhs)
        off_metric[m]=zdict({t:solved[idx[t]] for t in teams})
        def_metric[m]=zdict({t:solved[n+idx[t]] for t in teams})
        convergence[m]={"iterations":1,"max_delta":0.0}
'''
script=original[:start]+replacement+original[end:]
script=script.replace('    calibration=json.loads(FCS_CALIBRATION.read_text())','    RIDGE=float(os.environ.get("RIDGE_PENALTY","4"))\n    calibration=json.loads(FCS_CALIBRATION.read_text())')
orig='OUT=ROOT/"data"/"experiments"/f"recursive_unit_strength_v15_{SEASON}_week_{WEEK}.json"'
assert orig in script
script=script.replace(orig,'OUT=ROOT/"data"/"experiments"/f"nfl_ridge_joint_{os.environ.get(\'RIDGE_LABEL\',\'4\')}_{SEASON}_week_{WEEK}.json"')
tmp=root/'_research_nfl_ridge_runtime.py'
tmp.write_text(script)
variants=[('2',2.0),('4',4.0),('8',8.0)]
try:
 for label,penalty in variants:
  subprocess.run([sys.executable,str(tmp)],check=True,env=dict(os.environ,MODEL_WEEK='7',RIDGE_LABEL=label,RIDGE_PENALTY=str(penalty)),timeout=750)
finally:tmp.unlink(missing_ok=True)
v15=json.loads((root/'data/experiments/recursive_unit_strength_v15_2026_week_7.json').read_text())['rankings']
reference={r['team']:r for r in v15}
summary=[]
for label,penalty in variants:
 rows=json.loads((root/f'data/experiments/nfl_ridge_joint_{label}_2026_week_7.json').read_text())['rankings']
 ix={r['team']:r for r in rows}
 summary.append({'ridge':penalty,'top15':[{'team':r['team'],'rank':r['rank'],'sd':r['overall_team_strength_sd'],'v15_rank':reference[r['team']]['rank']} for r in rows[:15]],'focus':[{'team':t,'rank':ix[t]['rank'],'v15_rank':reference[t]['rank'],'sd':ix[t]['overall_team_strength_sd']} for t in ('Miami','Notre Dame','Utah','Texas Tech','New Mexico','Liberty') ]})
report={'model':'nfl-style-joint-ridge-cfb-research','year':2026,'through_week':6,'comparison':'Production v15 vs one-pass joint ridge regularization, same full CFB metric set and game population','qualification':'Unlike CFB v15, the NFL methodology jointly fits offense and defense by ridge regression rather than iterative opponent-unit adjustments. FCS downside is approximated as a one-sided pseudo-observation. Ridge settings are sensitivity probes, not historically optimized.','production_unchanged':True,'v15_top15':[{'rank':x['rank'],'team':x['team'],'sd':x['overall_team_strength_sd']} for x in v15[:15]],'variants':summary}
(root/'data/experiments/nfl_ridge_joint_comparison_2026.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
