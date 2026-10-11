#!/usr/bin/env python3
"""Research-only comparison: 90/10 separate MOV versus per-game metrics adjustment."""
import os,json,pathlib,subprocess,sys,urllib.request,urllib.parse,statistics,collections,math
R=pathlib.Path(__file__).resolve().parent
d=(R/'run_temporal_opponent_strength_research.py').read_text()
ns={'__file__':str(R/'run_temporal_opponent_strength_research.py')}
exec(compile(d.split('variants=[]',1)[0],'<prepare>','exec'),ns)
src=ns['src']
for a,b in {
 'adjusted_evidence(z,comp_def.get(o,0),sens)':'adjusted_evidence(z,pregame_def.get((t,o),0),sens)',
 'adjusted_evidence(-z,comp_off.get(o,0),sens)':'adjusted_evidence(-z,pregame_off.get((t,o),0),sens)',
 'game_category_strength(own,comp_def.get(o,0.0))':'game_category_strength(own,pregame_def.get((t,o),0.0))',
 'game_category_strength(opp,comp_off.get(o,0.0),defensive=True)':'game_category_strength(opp,pregame_off.get((t,o),0.0),defensive=True)',
 'opp_sd=max(-2.5,min(2.5,base_overall[opponent]))':'opp_sd=max(-2.5,min(2.5,pregame_strength.get((opponent,t),0.0)))',
 'ex=1/(1+math.exp(-1.2*(base_overall[home]-base_overall[away])))':'ex=1/(1+math.exp(-1.2*(pregame_strength.get((home,away),0.0)-pregame_strength.get((away,home),0.0))))',
 'h_opp=max(-2.5,min(2.5,base_overall[away]))':'h_opp=max(-2.5,min(2.5,pregame_strength.get((away,home),0.0)))',
 'a_opp=max(-2.5,min(2.5,base_overall[home]))':'a_opp=max(-2.5,min(2.5,pregame_strength.get((home,away),0.0)))'
}.items():src=src.replace(a,b)
src=src.replace('hybrid_weighted_symmetric_csc_75_15_10_2026_week_7.json','research_mov_control_2026_week_7.json')
p=R/'_research_mov_control.py';p.write_text(src)
try:subprocess.run([sys.executable,str(p)],check=True,env=dict(os.environ,MODEL_WEEK='7'),timeout=1300)
finally:p.unlink(missing_ok=True)
base=json.loads((R/'data/experiments/research_mov_control_2026_week_7.json').read_text())
baseline={r['team']:r for r in base['rankings']}
key=os.environ['CFBD_API_KEY']
req=urllib.request.Request('https://api.collegefootballdata.com/lines?year=2026&seasonType=regular',headers={'Authorization':'Bearer '+key,'Accept':'application/json'})
with urllib.request.urlopen(req,timeout=120) as f:markets=json.load(f)
hist=json.loads((R/'data/historical/2026.json').read_text())['games']
eligible={g['team'] for g in base['rankings']}
games={str(g['game_id']):g for g in hist if g.get('result') and 0<int(g.get('week') or 0)<7 and g.get('home') in eligible and g.get('away') in eligible}
records=collections.defaultdict(list)
audit=[]
for row in markets:
 gid=str(row.get('id'))
 if gid not in games:continue
 g=games[gid];pp=sorted((x for x in row.get('lines',[]) if x.get('spread') is not None),key=lambda x:(0 if 'consensus' in str(x.get('provider','')).lower() else 1,0 if 'draftkings' in str(x.get('provider','')).lower() else 1,str(x.get('provider',''))))
 if not pp:continue
 try:spread=float(pp[0]['spread'])
 except (ValueError,TypeError):continue
 margin=float(g['result']['home_points'])-float(g['result']['away_points'])
 residual=max(-35,min(35,margin+spread))
 records[g['home']].append(residual);records[g['away']].append(-residual)
 audit.append({'game_id':gid,'home':g['home'],'away':g['away'],'residual':residual,'spread':spread})
raw={t:(sum(records[t])/(len(records[t])+4) if records[t] else None) for t in eligible}
vals=[v for v in raw.values() if v is not None]
mu=statistics.fmean(vals);sigma=statistics.pstdev(vals)
mov={t:((raw[t]-mu)/sigma if raw[t] is not None else None) for t in eligible}
# Arm B: the separately weighted, 10% MOV component already tested.
separate={t:(.9*baseline[t]['overall_team_strength_sd']+.1*mov[t] if mov[t] is not None else baseline[t]['overall_team_strength_sd']) for t in eligible}
# Arm C: GAME-BY-GAME MOV modifies each statistical observation, rather than
# an additive season-end component. To preserve categories and opposite signs,
# add identical normalized MOV evidence to each available metric *at game level*.
# This is a research proxy for a universal per-stat modifier, not an optimized model.
shifts={}
for x in audit:
 v=max(-2.0,min(2.0,x['residual']/14.0))
 shifts[(x['home'],x['away'])]=v
 shifts[(x['away'],x['home'])]=-v
# Use game-level shifts in the metric observations before category recomposition
# by inserting them at the game-metric constructor. All metrics receive the same
# standardized residual sign, avoiding dimension-dependent raw-number multipliers.
embedded='    MOV_GAME_SHIFTS='+repr(shifts)+'\n'
anchor='    game_metric={}'
assert anchor in src
mainsrc=src.replace(anchor,embedded+anchor)
needle='(hm[m]-mus[m])/sds[m]'
assert needle in mainsrc
mainsrc=mainsrc.replace('games_m.append((h,a,(hm[m]-mus[m])/sds[m]))','games_m.append((h,a,(hm[m]-mus[m])/sds[m]+0.10*MOV_GAME_SHIFTS.get((h,a),0.0)))')
mainsrc=mainsrc.replace('games_m.append((a,h,(am[m]-mus[m])/sds[m]))','games_m.append((a,h,(am[m]-mus[m])/sds[m]+0.10*MOV_GAME_SHIFTS.get((a,h),0.0)))')
mainsrc=mainsrc.replace('g.append((h,a,(hm[m]-mus[m])/sds[m]))','g.append((h,a,(hm[m]-mus[m])/sds[m]+0.10*MOV_GAME_SHIFTS.get((h,a),0.0)))')
mainsrc=mainsrc.replace('g.append((a,h,(am[m]-mus[m])/sds[m]))','g.append((a,h,(am[m]-mus[m])/sds[m]+0.10*MOV_GAME_SHIFTS.get((a,h),0.0)))')
# Do not inject season-level MOV into CSC. Here MOV changes the 75% statistical
# metric evidence and its derived team O/D units only.
mainsrc=mainsrc.replace('research_mov_control_2026_week_7.json','research_mov_allmetrics_2026_week_7.json')
q=R/'_research_mov_allmetrics.py';q.write_text(mainsrc)
try:subprocess.run([sys.executable,str(q)],check=True,env=dict(os.environ,MODEL_WEEK='7'),timeout=1300)
finally:q.unlink(missing_ok=True)
every=json.loads((R/'data/experiments/research_mov_allmetrics_2026_week_7.json').read_text())
allm={r['team']:r for r in every['rankings']}
def rank(scores):return {t:i+1 for i,t in enumerate(sorted(scores,key=lambda t:(-scores[t],t)))}
ranksep=rank(separate)
baseorder=sorted(eligible,key=lambda t:baseline[t]['rank'])
rows=[]
for t in baseorder:
 rows.append({'team':t,'baseline':baseline[t]['rank'],'separate_mov':ranksep[t],
 'all_metrics_mov':allm[t]['rank'],'baseline_offense':baseline[t]['offense_rank'],'allmetrics_offense':allm[t]['offense_rank'],
 'baseline_defense':baseline[t]['defense_rank'],'allmetrics_defense':allm[t]['defense_rank'],
 'mov_sd':round(mov[t],3) if mov[t] is not None else None,'games_with_lines':len(records[t])})
focus=['New Mexico','SMU','Oklahoma','Texas','Georgia','Ohio State','Miami','Notre Dame','Oregon']
report={'study':'Frozen-pregame MOV 10% comparison: baseline vs separate component vs per-game universal metric shift',
 'through_week':6,'eligible_market_games':len(audit),'three_arms':{
 'A':'Existing frozen-pregame 75/15/10 hybrid without closing MOV',
 'B':'90% existing overall plus 10% standardized mean spread residual',
 'C':'Add 0.10*(per-game spread residual/14, clipped +/-2 SD) into every available statistical metric z before opponent correction and aggregation; retains all other original model components'},
 'important_limitations':['Arm C is a same-direction additive z-shift proxy for applying MOV to all metrics, not multiplying raw observations by their differing units','Arm C 0.10 injection is not directly mathematically equivalent in final overall weight to Arm B 10% blend','Some original component metrics and residual result signals already count scoring and results; Arm C can double-count','Market lines are not independently timestamp-certified closing lines','Results are in-sample rank sensitivity only; not out-of-sample accuracy'],
 'focus':[next(x for x in rows if x['team']==t) for t in focus],
 'baseline_top25':baseorder[:25], 'separate_top25':sorted(eligible,key=lambda t:ranksep[t])[:25],
 'allmetrics_top25':sorted(eligible,key=lambda t:allm[t]['rank'])[:25],
 'rankings':rows}
out=R/'data/experiments/compare_mov_separate_vs_allmetrics_2026.json'
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'games':len(audit),'focus':report['focus'],'top25':{k:report[k] for k in ('baseline_top25','separate_top25','allmetrics_top25')}},indent=2))
