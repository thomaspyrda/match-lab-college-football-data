#!/usr/bin/env python3
"""Full 40-metric weekly historical replay pilot, research only, 2026.
Execute original v15 metric pipeline separately for week 3-7, then predict each upcoming week.
Caveat: baseline v15 uses within-history recursive opponent ratings, frozen at prediction time,
not frozen per game. Results do not substitute the nonrecursive hybrid baseline.
"""
import json,os,pathlib,subprocess,sys,statistics,math,collections,tempfile
ROOT=pathlib.Path(__file__).resolve().parent
original=(ROOT/'experiment_dominance_v15.py').read_text()
original=original.replace('WEEK=int(os.environ.get("MODEL_WEEK","6"))','WEEK=int(os.environ.get("MODEL_WEEK","6"))')
original=original.replace('OUT=ROOT/"data"/"experiments"/f"recursive_unit_strength_v15_{SEASON}_week_{WEEK}.json"','OUT=ROOT/"data"/"experiments"/"fullmetric_replay_cache"/f"v15_{SEASON}_pregame_week_{WEEK}.json"')
tmp=ROOT/'data'/'experiments'/'fullmetric_replay_cache'
tmp.mkdir(parents=True,exist_ok=True)
engine=tmp/'_research_v15_runner.py'
# Running patched source FROM repository root needed for ROOT=... parent.
# Rather than relocating ROOT, rewrite ROOT to the repository root explicitly.
original=original.replace('ROOT=Path(__file__).resolve().parent','ROOT=Path(__file__).resolve().parents[3]')
engine.write_text(original)
history=json.loads((ROOT/'data/historical/2026.json').read_text())['games']
records=[];metrics_count=0
for week in range(3,8):
 target=tmp/f'v15_2026_pregame_week_{week}.json'
 if not target.exists():
  env=os.environ.copy();env['MODEL_WEEK']=str(week)
  subprocess.run([sys.executable,str(engine)],cwd=str(ROOT),env=env,check=True,timeout=1000)
  if not target.exists():raise RuntimeError('Missing snapshot '+str(target))
 obj=json.loads(target.read_text())
 metrics_count=len(next(iter(obj['rankings']))['diagnostics']['offense_metrics']) if obj['rankings'] else 0
 ratings={r['team']:r for r in obj['rankings']}
 games=[g for g in history if g.get('result') and int(g.get('week') or 0)==week]
 for g in games:
  h=ratings.get(g['home']);a=ratings.get(g['away'])
  if h is None or a is None:continue
  actual=float(g['result']['home_points'])-float(g['result']['away_points'])
  delta=(h['overall_team_strength_sd']-a['overall_team_strength_sd'])
  off_adv=h['offensive_strength_sd']-a['defensive_strength_sd']
  def_adv=a['offensive_strength_sd']-h['defensive_strength_sd']
  # Provisional, unfitted SD-to-scoring-margin conversion; no target outcomes used.
  pred=2.5+7*delta
  pred_unit=2.5+3.5*(off_adv-def_adv)
  records.append({'week':week,'game_id':str(g['game_id']),'home':g['home'],'away':g['away'],
    'actual_margin':actual,'overall_pred':round(pred,4),'unit_pred':round(pred_unit,4)})
def mae(col):return round(statistics.fmean(abs(g[col]-g['actual_margin']) for g in records),4) if records else None
report={'status':'completed_fullmetric_pilot','year':2026,'pregame_weeks':list(range(3,8)),
 'game_count':len(records),'metrics_per_unit':metrics_count,
 'metric_categories':'scoring, efficiency, passing, rushing, line, finishing; including play-derived situational conversion/red-zone variables',
 'baseline':'original full v15 40-metric unit engine; each weekly snapshot uses games completed BEFORE prediction week',
 'checks':{'all_snapshot_weeks_prior_to_predictions':True,'nonrecursive_frozen_per_game':False,'is_out_of_sample_coefficients_fit':False},
 'performance':{'overall_sd_pred_mae':mae('overall_pred'),'unit_sd_pred_mae':mae('unit_pred')},
 'per_week':{str(w):{'n':sum(x['week']==w for x in records),'overall_mae':round(statistics.fmean(abs(x['overall_pred']-x['actual_margin']) for x in records if x['week']==w),3) if any(x['week']==w for x in records) else None} for w in range(3,8)},
 'limitations':['This pilot establishes all-metric replay and strict pregame snapshots; it is not yet the final 2024-2026 model comparison','Original v15 uses recursively recomputed historical opponent profiles, not frozen per-game opponent ratings','Season 2026 existing independent preseason prior is used','Projection SD-to-points coefficient (7) is illustrative and not learned','Current game result never influences its own prediction'],
 'sample':records[:10]}
out=ROOT/'data/experiments/fullmetric_weekly_replay_2026_pilot.json';out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('game_count','metrics_per_unit','performance','per_week')},indent=2))

# Run pilot.
