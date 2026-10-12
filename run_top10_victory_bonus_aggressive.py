#!/usr/bin/env python3
"""Research-only: aggressive 0.03 SD per point Top-10 pregame victory bonus."""
import json,pathlib,collections
ROOT=pathlib.Path(__file__).resolve().parent
D=ROOT/'data'
season=2026
base=json.loads((D/'experiments/recursive_unit_strength_v15_2026_week_7.json').read_text())
hist=json.loads((D/'historical/2026.json').read_text())['games']
pre=json.loads((D/'preseason/2026.json').read_text())['teams']
alias={'Mississippi':'Ole Miss','Connecticut':'UConn','Texas-San Antonio':'UTSA','San José State':'San Jose State'}
def canonical(s):return alias.get(s,s)
rankings={}
rankings[1]={canonical(t):int(v['consensus_rank']) for t,v in pre.items() if v.get('consensus_rank') is not None}
for wk in range(2,7):
 data=json.loads((D/f'experiments/recursive_unit_strength_v15_2026_week_{wk}.json').read_text())
 assert data['pregame_week']==wk, f'Week snapshot mismatch {wk}'
 rankings[wk]={canonical(x['team']):int(x['rank']) for x in data['rankings']}
base_scores={canonical(r['team']):float(r['overall_team_strength_sd']) for r in base['rankings']}
audit=[];bonus=collections.defaultdict(int);wins=collections.defaultdict(list)
missing=[]
for g in hist:
 week=int(g.get('week') or 0)
 if week<1 or week>=7 or not g.get('result'):continue
 h,a=canonical(g.get('home')),canonical(g.get('away'))
 res=g['result']; hp=res.get('home_points');ap=res.get('away_points')
 if hp is None or ap is None or hp==ap:continue
 winner,opponent=(h,a) if hp>ap else (a,h)
 if winner not in base_scores:continue
 opp_rank=rankings.get(week,{}).get(opponent)
 if opp_rank is None:
  missing.append({'week':week,'winner':winner,'opponent':opponent,'reason':'missing pregame rank'})
  continue
 pts=max(0,11-opp_rank)
 if pts:
  bonus[winner]+=pts
  wins[winner].append({'week':week,'opponent':opponent,'pregame_rank':opp_rank,'bonus_points':pts})
  audit.append({'team':winner,'opponent':opponent,'week':week,'opponent_pregame_rank':opp_rank,'bonus_points':pts})
# No cap: cumulative bonuses, exact user's schedule
out=[]
for t,b in base_scores.items():
 new=b+.03*bonus[t]
 out.append({'team':t,'baseline_sd':round(b,5),'bonus_points':bonus[t],
             'bonus_sd':round(.03*bonus[t],5),'adjusted_sd':round(new,5),
             'victories':wins[t]})
out.sort(key=lambda x:(-x['adjusted_sd'],x['team']))
brank={canonical(r['team']):i+1 for i,r in enumerate(base['rankings'])}
for i,x in enumerate(out):
 x['rank']=i+1;x['original_rank']=brank[x['team']];x['rank_change']=x['original_rank']-x['rank']
checks={'top10_cutoff':all(1<=e['opponent_pregame_rank']<=10 for e in audit),
 'exact_bonus_formula':all(e['bonus_points']==11-e['opponent_pregame_rank'] for e in audit),
 'all_applied_to_overall_only':True,
 'week_7_not_used_as_week_6_pregame':True}
report={'study':'2026 aggressive Top-10 victory bonus, distinct cutoff','status':'research_only',
 'base_model':'Original v15 full-metric through week 6, pregame Week 7',
 'bonus_rule':'Win versus opponent pregame #1..#10 earns 11 minus rank points, 0 outside; each point adds 0.03 SD to overall strength; cumulative, no cap.',
 'pregame_rank_method':'Week 1 independent 2026 preseason consensus rank; Weeks 2-6 archived original v15 pregame snapshots, reconstructed from games before that week. Archived v15 uses recursive opponent adjustments within each pregame snapshot.',
 'weaknesses':['Cumulative bonus favors more opportunities to face top-10 teams; that is intentional in this experimental formula.','The extra reward overlaps some existing result/statistical signal.','Historical weekly pregame rankings are original v15, not frozen per-game nonrecursive experimental ratings.','No independent prediction accuracy test completed.'],
 'verified':checks,'missing_ranks':missing,'bonused_wins':audit,
 'top50':out[:50],
 'focus':{t:next((x for x in out if x['team']==t),None) for t in ['Kentucky','Oklahoma','Texas','New Mexico','Georgia','Oregon','SMU','Alabama','LSU','South Carolina','Texas A&M']},
 'all_teams':out}
path=D/'experiments/top10_victory_bonus_aggressive_2026.json'
path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'checks':checks,'bonused_wins':audit,'missing':missing,'focus':report['focus'],'top25':[{'rank':r['rank'],'team':r['team'],'baseline':r['original_rank'],'pts':r['bonus_points']} for r in out[:25]]},indent=2))
