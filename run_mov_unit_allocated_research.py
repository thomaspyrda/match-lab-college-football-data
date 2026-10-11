#!/usr/bin/env python3
"""Research-only: allocate game MOV residual to offense/defense using frozen pregame unit evidence."""
import os,json,pathlib,subprocess,sys,urllib.request,collections,statistics,math
R=pathlib.Path(__file__).resolve().parent
source=(R/'run_compare_mov_allmetrics.py').read_text()
# reuse exact baseline builder, but stop before separate-MOV and universal modifier calculations
prefix=source.split('# Arm B: the separately weighted',1)[0]
ns={'__file__':str(R/'run_compare_mov_allmetrics.py')}
exec(compile(prefix,'<shared-baseline>','exec'),ns)
baseline=ns['baseline']; mov=ns['mov']; audit=ns['audit']; eligible=ns['eligible']
full=ns['base']
details=full['competitive_strength_credit']['details']
per=collections.defaultdict(list)
events=[]
for x in audit:
    h,a=x['home'],x['away']
    residual=x['residual']
    for t,opp,rr in ((h,a,residual),(a,h,-residual)):
        matches=[g for g in details[t]['games'] if g['opponent']==opp]
        if len(matches)!=1:continue
        g=matches[0]
        off=g.get('offensive_game_signal');deff=g.get('defensive_game_signal')
        if off is None or deff is None: continue
        # For positive MOV assign more weight to stronger above-expectation unit.
        # For negative MOV assign more blame to weaker unit.
        arg=max(-6,min(6,(float(off)-float(deff))*(1 if rr>=0 else -1)))
        oshare=1/(1+math.exp(-arg));dshare=1-oshare
        ocontrib=2*oshare*rr
        dcontrib=2*dshare*rr
        per[t].append((ocontrib,dcontrib))
        events.append({'team':t,'opponent':opp,'mov_residual':rr,'offense_signal':off,'defense_signal':deff,'offense_share':round(oshare,3),'offense_contribution':round(ocontrib,3),'defense_contribution':round(dcontrib,3)})
def stabilized(k):
    return {t:(sum(p[k] for p in per[t])/(len(per[t])+4) if per[t] else None) for t in eligible}
oraw=stabilized(0);draw=stabilized(1)
def z(v):
    valid=[x for x in v.values() if x is not None]
    mu=statistics.fmean(valid);sd=statistics.pstdev(valid)
    return {t:( (v[t]-mu)/sd if v[t] is not None and sd else None) for t in eligible}
oz=z(oraw);dz=z(draw)
o={t:(.9*baseline[t]['offensive_strength_sd']+.1*oz[t] if oz[t] is not None else baseline[t]['offensive_strength_sd']) for t in eligible}
dd={t:(.9*baseline[t]['defensive_strength_sd']+.1*dz[t] if dz[t] is not None else baseline[t]['defensive_strength_sd']) for t in eligible}
combined={t:(o[t]+dd[t])/2 for t in eligible}
def order(v):return sorted(eligible,key=lambda t:(-v[t],t))
ro={t:i+1 for i,t in enumerate(order(o))}
rd={t:i+1 for i,t in enumerate(order(dd))}
rt={t:i+1 for i,t in enumerate(order(combined))}
previous=json.loads((R/'data/experiments/compare_mov_separate_vs_allmetrics_2026.json').read_text())
prev={r['team']:r for r in previous['rankings']}
rows=[{'team':t,'baseline':baseline[t]['rank'],'separate':prev[t]['separate_mov'],'universal':prev[t]['all_metrics_mov'],
       'allocated':rt[t],'offense_before':baseline[t]['offense_rank'],'offense_allocated':ro[t],
       'defense_before':baseline[t]['defense_rank'],'defense_allocated':rd[t],
       'offense_mov_z':round(oz[t],3) if oz[t] is not None else None,
       'defense_mov_z':round(dz[t],3) if dz[t] is not None else None,
       'covered_games':len(per[t])}
      for t in sorted(eligible,key=lambda t:baseline[t]['rank'])]
focus=['Miami','Notre Dame','Georgia','Ohio State','Utah','Alabama','Texas','Oregon','Oklahoma','SMU','New Mexico']
report={'study':'Game-level allocated MOV versus separate and universal MOV','through_week':6,'eligible_spread_games':len(audit),
 'model':'90% pregame offense and defense plus 10% separate allocated MOV on each unit; overall 50/50',
 'allocation':'For each game, softmax of frozen pregame adjusted offensive versus defensive game signals assigns positive residual to stronger-performing unit and negative residual to weaker-performing unit; unit scores sum to 2x MOV residual so equal units reproduce the raw effect.',
 'sample_reliability':'4-game shrinkage within each unit prior to FBS standardization',
 'limitations':['Not a prospective accuracy validation','Closing spreads not timestamp certified','Per-game unit signals are drawn from full-season standardized metrics, so the score is not strictly leakage-free','Previously modeled 75/15/10 baseline contains result-related components; adding MOV may overlap','Offensive and defensive attribution is heuristic, not proven causal','Some games can be missing unit signals'],
 'focus':[next(x for x in rows if x['team']==t) for t in focus],
 'baseline_top25':previous['baseline_top25'],'separate_top25':previous['separate_top25'],
 'universal_top25':previous['allmetrics_top25'],'allocated_top25':order(combined)[:25],
 'rankings':rows,'events':events}
out=R/'data/experiments/mov_unit_allocated_comparison_2026.json'
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'eligible_spread_games':len(audit),'allocated_team_games':len(events),'focus':report['focus'],'allocated_top25':report['allocated_top25']},indent=2))
