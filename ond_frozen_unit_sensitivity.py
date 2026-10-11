#!/usr/bin/env python3
"""Research only: compare live v15 recursive per-metric opponent units to frozen
pre-existing opponent offensive/defensive unit SD in an upcoming-week snapshot.
No production outputs modified. Historical predictive validation is separate.
"""
import json,subprocess,sys,os,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
src=(ROOT/'experiment_dominance_v15.py').read_text()
base=json.loads((ROOT/'data/experiments/recursive_unit_strength_v15_2026_week_7.json').read_text())
# Week 6 pregame opponent ratings provide historical lagged independent units;
# for full historical pregame correctness, per-game week snapshots are required.
prior=json.loads((ROOT/'data/experiments/recursive_unit_strength_v15_2026_week_6.json').read_text())
pr={r['team']:r for r in prior['rankings']}
prior_map={t:{'off':r['offensive_strength_sd'],'def':r['defensive_strength_sd']} for t,r in pr.items()}
new=src
needle='    hist=json.loads(HISTORY.read_text())["games"]'
assert needle in new
new=new.replace(needle,'    fixed_units=json.loads((ROOT/"data"/"experiments"/"ond_frozen_units_week6.json").read_text())\n'+needle)
a='deff.get(o,0.0)';b='off.get(offense,0.0)'
assert new.count(a)==1 and new.count(b)==1
new=new.replace(a,'fixed_units.get(o,{}).get("def",0.0)').replace(b,'fixed_units.get(offense,{}).get("off",0.0)')
co='mult_calibration["metrics"].get(m,{}).get("selected_coefficient",0.20)'
assert new.count(co)==2
results=[]
for mult in (0.75,1.0,1.25):
 label=str(mult).replace('.','p')
 version=new.replace(co,f'({co})*{mult}')
 target=f'ond_frozen_units_{label}_2026_week_7.json'
 version=version.replace('OUT=ROOT/"data"/"experiments"/f"recursive_unit_strength_v15_{SEASON}_week_{WEEK}.json"',f'OUT=ROOT/"data"/"experiments"/"{target}"')
 assert target in version
 temp=ROOT/f'_ond_frozen_{label}.py'
 temp.write_text(version)
 try:subprocess.run([sys.executable,str(temp)],check=True,env=dict(os.environ,MODEL_WEEK='7'),timeout=650)
 finally:temp.unlink(missing_ok=True)
 rows=json.loads((ROOT/'data/experiments'/target).read_text())['rankings']
 by={r['team']:r for r in rows}
 compare={r['team']:r for r in base['rankings']}
 selected=[]
 for name in ('Miami','Texas Tech','New Mexico','Liberty','Alabama','Georgia','Notre Dame','Utah'):
  r=by[name];v=compare[name]
  selected.append({'team':name,'rank':r['rank'],'v15_rank':v['rank'],'sd':r['overall_team_strength_sd'],'v15_sd':v['overall_team_strength_sd'],'rank_change':v['rank']-r['rank']})
 results.append({'coefficient_multiplier':mult,'top10':[r['team'] for r in rows[:10]],'focus':selected})
report={'type':'frozen unit strength sensitivity','snapshot':'week6 pregame unit strengths, used to adjust games through week6 (NOT fully pregame safe for games before week6)','v15_reference':'week7','limitations':'Diagnostic only: week6 snapshot includes future games relative to weeks1-5, thus is not an independent predictive backtest. Full historical per-game frozen snapshots needed. Baseline v15 uses recursively solved metric-specific units; this experiment uses composite unit SD instead.','variants':results,'production_unchanged':True}
path=ROOT/'data/experiments/ond_frozen_unit_comparison_2026.json'
path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
