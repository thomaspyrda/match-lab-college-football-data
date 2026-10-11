#!/usr/bin/env python3
"""Research only: 90% frozen-pregame model + 10% closing-line MOV residual."""
import json, pathlib, os, subprocess, sys, urllib.request, urllib.parse, collections, statistics, math
ROOT=pathlib.Path(__file__).resolve().parent
namespace={'__file__':str(ROOT/'run_temporal_opponent_strength_research.py')}
driver=(ROOT/'run_temporal_opponent_strength_research.py').read_text()
exec(compile(driver.split('variants=[]',1)[0],'<prep>','exec'),namespace)
src=namespace['src']
reps={
 'adjusted_evidence(z,comp_def.get(o,0),sens)':'adjusted_evidence(z,pregame_def.get((t,o),0),sens)',
 'adjusted_evidence(-z,comp_off.get(o,0),sens)':'adjusted_evidence(-z,pregame_off.get((t,o),0),sens)',
 'game_category_strength(own,comp_def.get(o,0.0))':'game_category_strength(own,pregame_def.get((t,o),0.0))',
 'game_category_strength(opp,comp_off.get(o,0.0),defensive=True)':'game_category_strength(opp,pregame_off.get((t,o),0.0),defensive=True)',
 'opp_sd=max(-2.5,min(2.5,base_overall[opponent]))':'opp_sd=max(-2.5,min(2.5,pregame_strength.get((opponent,t),0.0)))',
 'ex=1/(1+math.exp(-1.2*(base_overall[home]-base_overall[away])))':'ex=1/(1+math.exp(-1.2*(pregame_strength.get((home,away),0.0)-pregame_strength.get((away,home),0.0))))',
 'h_opp=max(-2.5,min(2.5,base_overall[away]))':'h_opp=max(-2.5,min(2.5,pregame_strength.get((away,home),0.0)))',
 'a_opp=max(-2.5,min(2.5,base_overall[home]))':'a_opp=max(-2.5,min(2.5,pregame_strength.get((home,away),0.0)))'
}
for a,b in reps.items():src=src.replace(a,b)
src=src.replace('hybrid_weighted_symmetric_csc_75_15_10_2026_week_7.json','mov_pregame_baseline_2026_week_7.json')
runtime=ROOT/'_mov_research_runtime.py'
runtime.write_text(src)
try:subprocess.run([sys.executable,str(runtime)],env=dict(os.environ,MODEL_WEEK='7'),check=True,timeout=1300)
finally:runtime.unlink(missing_ok=True)
base=json.loads((ROOT/'data/experiments/mov_pregame_baseline_2026_week_7.json').read_text())
baseline={r['team']:r for r in base['rankings']}
KEY=os.environ.get('CFBD_API_KEY')
if not KEY:raise RuntimeError('Missing CFBD_API_KEY')
def get(path,**kwargs):
    url='https://api.collegefootballdata.com'+path+'?'+urllib.parse.urlencode(kwargs)
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+KEY,'Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as f:return json.load(f)
hist=json.loads((ROOT/'data/historical/2026.json').read_text())['games']
played=[g for g in hist if g.get('result') and 0<int(g.get('week') or 0)<7]
by_id={str(g['game_id']):g for g in played}
lines=get('/lines',year=2026,seasonType='regular')
records=collections.defaultdict(list)
audits=[]
for row in lines:
    gid=str(row.get('id'))
    if gid not in by_id:continue
    game=by_id[gid]
    home=game['home'];away=game['away']
    if home not in baseline or away not in baseline:continue
    # Favor a recognized bookmaker with an explicit provider spread.
    providers=row.get('lines') or []
    ranked=sorted((p for p in providers if p.get('spread') is not None), key=lambda p:(0 if 'consensus' in str(p.get('provider','')).lower() else 1,0 if 'draftkings' in str(p.get('provider','')).lower() else 1,str(p.get('provider',''))))
    if not ranked:continue
    chosen=ranked[0]
    try:spread=float(chosen['spread'])
    except (TypeError,ValueError):continue
    result=game.get('result') or {}
    hp=result.get('home_points');ap=result.get('away_points')
    if hp is None or ap is None:continue
    # CFBD spread is home-team point spread: expected home margin = -spread
    residual=(float(hp)-float(ap))+spread
    residual=max(-35,min(35,residual))
    records[home].append(residual)
    records[away].append(-residual)
    audits.append({'week':game['week'],'game_id':gid,'home':home,'away':away,
                   'provider':chosen.get('provider'),'home_spread':spread,
                   'actual_home_margin':float(hp)-float(ap),'home_margin_residual':round(residual,2)})
if len(audits)<100:raise RuntimeError(f'Insufficient closing-line coverage: {len(audits)} games')
# Reliability shrinkage by 4 games, centered and standardized among covered teams.
raw={t:sum(records[t])/(len(records[t])+4) if records[t] else None for t in baseline}
available=[x for x in raw.values() if x is not None]
mu=statistics.fmean(available);sd=statistics.pstdev(available)
if sd<=0:raise RuntimeError('Zero MOV variation')
mov={t:(raw[t]-mu)/sd if raw[t] is not None else None for t in baseline}
# For missing lines, hold prior baseline value; never treat missing as zero evidence.
blended={t:(.9*r['overall_team_strength_sd']+.1*mov[t] if mov[t] is not None else r['overall_team_strength_sd']) for t,r in baseline.items()}
base_order=sorted(baseline,key=lambda t:baseline[t]['rank'])
new_order=sorted(baseline,key=lambda t:(-blended[t],t))
new_rank={t:i+1 for i,t in enumerate(new_order)}
rows=[{'team':t,'baseline_rank':baseline[t]['rank'],'mov_rank':new_rank[t],
       'change':baseline[t]['rank']-new_rank[t],
       'baseline_sd':baseline[t]['overall_team_strength_sd'],
       'mov_sd':round(mov[t],3) if mov[t] is not None else None,
       'combined_score':round(blended[t],3),'games_with_lines':len(records[t]),
       'offense_rank':baseline[t]['offense_rank'],'defense_rank':baseline[t]['defense_rank']} for t in base_order]
focus=['Miami','Notre Dame','Ohio State','Georgia','Utah','Texas','Alabama','Oklahoma','LSU']
report={'study':'Pregame baseline 90% plus standardized closing-spread MOV residual 10%',
 'status':'research only, no published model changes','through_week':6,
 'formula':'MOV residual = actual home scoring margin + home closing spread; opposite sign for away; capped +/-35; team mean shrunk by n/(n+4); standardized to FBS covered-team SD',
 'blend':{'pregame_model':0.90,'closing_mov':0.10},
 'covered_games':len(audits),'teams_with_lines':sum(bool(records[t]) for t in baseline),
 'providers':'Consensus if available, else DraftKings if available, else sorted provider; provider consistency not guaranteed',
 'limitations':['CFBD /lines may represent available market lines, not timestamp-certified exact kickoff closes','Pregame baseline normalization uses all earlier games through week 6, not strictly walk-forward','10% applies to final overall rating; offensive and defensive ranks remain original','Incomplete book coverage and line-source changes could bias residuals','This is a rankings sensitivity comparison, not a prospective predictive validation'],
 'baseline_top25':base_order[:25],'mov_top25':new_order[:25],
 'focus':[next(r for r in rows if r['team']==t) for t in focus],
 'largest_moves':sorted(rows,key=lambda r:abs(r['change']),reverse=True)[:25],
 'rankings':rows,'sample_lines':audits[:10]}
p=ROOT/'data/experiments/closing_mov_10pct_pregame_comparison_2026.json'
p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'covered_games':len(audits),'focus':report['focus'],'top25':new_order[:25]},indent=2))
