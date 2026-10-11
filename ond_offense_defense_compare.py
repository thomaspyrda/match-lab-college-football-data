#!/usr/bin/env python3
"""Experimental OND offense/defense composite on 2026 FBS games. No production writes.

Uses the independent OND offensive residual for a team and its opponent's opposite
residual in the same game for defensive performance. Descriptive, not forecast.
"""
import json,statistics,collections,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
raw=json.loads((ROOT/'data/experiments/ond_pilot_2026.json').read_text())
ranks=json.loads((ROOT/'data/experiments/recursive_unit_strength_v15_2026_week_7.json').read_text())['rankings']
byrank={r['team']:r for r in ranks}
index=collections.defaultdict(dict)
for r in raw['fbs_2026_dominance']:
 index[(r['game_id'],r['team'])][r['metric']]=r['dominance_residual_sd']
games=collections.defaultdict(lambda:{'offense':[],'defense':[],'opponent':None})
for r in raw['fbs_2026_dominance']:
 key=(r['team'],r['game_id'])
 games[key]['opponent']=r['opponent']
 games[key]['offense'].append(r['dominance_residual_sd'])
 opponent_score=index.get((r['game_id'],r['opponent']),{}).get(r['metric'])
 if opponent_score is not None:
  games[key]['defense'].append(-opponent_score)
perteam=collections.defaultdict(lambda:{'offense':[],'defense':[],'games':[]})
for (team,gid),g in games.items():
 if len(g['offense'])<8 or len(g['defense'])<8:continue
 o=statistics.fmean(g['offense']);d=statistics.fmean(g['defense'])
 perteam[team]['offense'].append(o);perteam[team]['defense'].append(d)
 perteam[team]['games'].append({'game_id':gid,'opponent':g['opponent'],'offense':round(o,3),'defense':round(d,3),'combined':round((o+d)/2,3)})
qualified=[]
for team,v in perteam.items():
 if len(v['games'])<2:continue
 o=statistics.fmean(v['offense']);d=statistics.fmean(v['defense'])
 qualified.append({'team':team,'n_games':len(v['games']),'offense':round(o,3),'defense':round(d,3),'combined':round((o+d)/2,3),'games':sorted(v['games'],key=lambda g:g['game_id'])})
for field,rankkey in [('offense','offense_rank'),('defense','defense_rank'),('combined','overall_rank')]:
 for n,r in enumerate(sorted(qualified,key=lambda x:x[field],reverse=True),1):r[rankkey]=n
for r in qualified:
 v=byrank.get(r['team'],{})
 r['v15_rank']=v.get('rank')
 r['v15_overall_sd']=v.get('overall_team_strength_sd')
 r['v15_offense_rank']=v.get('offense_rank')
 r['v15_defense_rank']=v.get('defense_rank')
qualified.sort(key=lambda r:r['overall_rank'])
focus={t:next((r for r in qualified if r['team']==t),None) for t in ('Miami','Texas Tech')}
report={'schema':'ond-offense-defense-pilot-v1','season':2026,'through_week':6,
 'qualifying_team_count':len(qualified),'method':'Game-level offense residual against pregame opponent allowed profile; defensive game residual = negative of opponent offense residual for the same metric. Equal offense/defense overall weight.',
 'sos_added':False,'fcs_policy':'FCS games excluded in this first combined comparison. No additional credit for FCS; separate below-expectation penalty calibration is still required.',
 'comparison_warning':'These ranks reflect only 13 overlapping advanced metrics with equal averaging, are not a direct apples-to-apples test of all v15 metrics or v15 overall standard deviation. Game scores are in 2025 validation residual-SD units.',
 'focus':focus,'top20':[{k:v for k,v in r.items() if k!='games'} for r in qualified[:20]],'all_teams':qualified}
dst=ROOT/'data/experiments/ond_offense_defense_2026.json'
dst.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'teams':len(qualified),'focus':focus,'top10':[{'team':r['team'],'rank':r['overall_rank']} for r in qualified[:10]]},indent=2))
