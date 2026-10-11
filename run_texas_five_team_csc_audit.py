#!/usr/bin/env python3
"""Research-only audit of five top-25 programs; no public rankings changes."""
import json, pathlib, math, statistics
ROOT=pathlib.Path(__file__).resolve().parent
p=ROOT/'data/experiments/hybrid_weighted_symmetric_csc_75_15_10_2026_week_7.json'
d=json.loads(p.read_text())
rows={x['team']:x for x in d['rankings']}
details=d['competitive_strength_credit']['details']
qrr=d['quality_results']['diagnostics']
names=['Texas','Georgia','Alabama','Ohio State','Oklahoma']
out=[]
for team in names:
 r=rows[team];games=details[team]['games']
 positive=sum(max(0,g['credit']) for g in games)
 negative=sum(min(0,g['credit']) for g in games)
 wins=sum(g['own_points']>g['opp_points'] for g in games)
 losses=sum(g['own_points']<g['opp_points'] for g in games)
 off=[g['offensive_game_signal'] for g in games if g['offensive_game_signal'] is not None]
 deff=[g['defensive_game_signal'] for g in games if g['defensive_game_signal'] is not None]
 quality_wins=[g for g in games if g['own_points']>g['opp_points'] and g['opponent_sd']>=.75]
 quality_losses=[g for g in games if g['own_points']<g['opp_points'] and g['opponent_sd']>=.75]
 out.append({'team':team,'rank':r['rank'],'strength_sd':r['overall_team_strength_sd'],'offense_rank':r['offense_rank'],'offensive_strength_sd':r['offensive_strength_sd'],'defense_rank':r['defense_rank'],'defensive_strength_sd':r['defensive_strength_sd'],'record':[wins,losses],'qrr_sd':qrr[team]['qrr_sd'],'csc_sd':details[team]['sd'],'total_positive_game_csc':round(positive,4),'total_negative_game_csc':round(negative,4),'positive_from_biggest_game_fraction':round(max((g['credit'] for g in games),default=0)/positive,4) if positive else 0,'mean_game_offense_signal':round(statistics.mean(off),4) if off else None,'mean_game_defense_signal':round(statistics.mean(deff),4) if deff else None,'qualified_strong_wins':len(quality_wins),'qualified_strong_losses':len(quality_losses),'games':games})
by_team={x['team']:x for x in out}
report={'name':'Texas Georgia Alabama Ohio State Oklahoma weighted CSC game-level audit','season':2026,'pregame_week':7,'through_week':6,'production_unchanged':True,'teams':out,'checks':{'texas_ohio_state_fraction_of_positive_csc':next(x['positive_from_biggest_game_fraction'] for x in out if x['team']=='Texas'),'texas_ou_loss_csc':next(g['credit'] for g in by_team['Texas']['games'] if g['opponent']=='Oklahoma'),'texas_ou_loss_qrr_surprise':next(g['result_surprise'] for g in by_team['Texas']['games'] if g['opponent']=='Oklahoma'),'texas_vs_georgia_offense_rank':[by_team['Texas']['offense_rank'],by_team['Georgia']['offense_rank']],'texas_vs_alabama_offense_rank':[by_team['Texas']['offense_rank'],by_team['Alabama']['offense_rank']]},'limitations':['CSC can reward good statistical performance in a loss while QRR penalizes that loss; intentional but must inspect combined magnitudes','2026 retrospective ratings; no out-of-sample ranking calibration','No game-level cap recalibration or ablations in this audit']}
q=ROOT/'data/experiments/texas_five_team_csc_audit_2026.json'
q.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'teams':[{k:x[k] for k in ('team','rank','offense_rank','defense_rank','qrr_sd','csc_sd','positive_from_biggest_game_fraction')} for x in out],'checks':report['checks']},indent=2))
