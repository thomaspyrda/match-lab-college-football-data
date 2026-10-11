#!/usr/bin/env python3
"""Research-only frozen-pregame baseline vs yardage-production enhancements."""
import json, os, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parent
# Reconstruct the previous experiment's exact source and frozen-opponent profiles.
driver=(ROOT/'run_temporal_opponent_strength_research.py').read_text()
prefix=driver.split('variants=[]',1)[0]
namespace={'__file__':str(ROOT/'run_temporal_opponent_strength_research.py')}
exec(compile(prefix,str(ROOT/'run_temporal_opponent_strength_research.py'),'exec'),namespace)
src=namespace['src']
assert 'pregame_off' in src and 'pregame_def' in src
target='data/experiments/production_volume_pregame_comparison_2026.json'
def run(label,extra):
    s=src.replace('hybrid_weighted_symmetric_csc_75_15_10_2026_week_7.json',
       'volume_'+label+'_75_15_10_2026_week_7.json')
    s=s.replace('    HYBRID_COEFF=1.0','    HYBRID_COEFF=1.0')
    # Keep identical frozen pregame opponent adjustments in both arms.
    replacements={
       'adjusted_evidence(z,comp_def.get(o,0),sens)':'adjusted_evidence(z,pregame_def.get((t,o),0),sens)',
       'adjusted_evidence(-z,comp_off.get(o,0),sens)':'adjusted_evidence(-z,pregame_off.get((t,o),0),sens)',
       'game_category_strength(own,comp_def.get(o,0.0))':'game_category_strength(own,pregame_def.get((t,o),0.0))',
       'game_category_strength(opp,comp_off.get(o,0.0),defensive=True)':'game_category_strength(opp,pregame_off.get((t,o),0.0),defensive=True)',
       'opp_sd=max(-2.5,min(2.5,base_overall[opponent]))':'opp_sd=max(-2.5,min(2.5,pregame_strength.get((opponent,t),0.0)))',
       'ex=1/(1+math.exp(-1.2*(base_overall[home]-base_overall[away])))':'ex=1/(1+math.exp(-1.2*(pregame_strength.get((home,away),0.0)-pregame_strength.get((away,home),0.0))))',
       'h_opp=max(-2.5,min(2.5,base_overall[away]))':'h_opp=max(-2.5,min(2.5,pregame_strength.get((away,home),0.0)))',
       'a_opp=max(-2.5,min(2.5,base_overall[home]))':'a_opp=max(-2.5,min(2.5,pregame_strength.get((home,away),0.0)))',
    }
    for before,after in replacements.items():s=s.replace(before,after)
    if extra:
        # Integrate total pass/rush gained into existing category budgets, not a seventh category.
        # PBP includes sacks among pass plays consistently with earlier yards-per-play code.
        s=s.replace('"passing_yards_per_play","passing_first_down_rate"',
           '"passing_yards_per_play","passing_first_down_rate","passing_yards_per_game"')
        s=s.replace('"rushing_yards_per_play","rushing_first_down_rate"',
           '"rushing_yards_per_play","rushing_first_down_rate","rushing_yards_per_game"')
        s=s.replace('"passing_yards_per_play":rate(sum(float(p.get("yardsGained") or 0) for p in passes),len(passes)),',
           '"passing_yards_per_play":rate(sum(float(p.get("yardsGained") or 0) for p in passes),len(passes)),\n      "passing_yards_per_game":sum(float(p.get("yardsGained") or 0) for p in passes) if scr else None,')
        s=s.replace('"rushing_yards_per_play":rate(sum(float(p.get("yardsGained") or 0) for p in rushes),len(rushes)),',
           '"rushing_yards_per_play":rate(sum(float(p.get("yardsGained") or 0) for p in rushes),len(rushes)),\n      "rushing_yards_per_game":sum(float(p.get("yardsGained") or 0) for p in rushes) if scr else None,')
        assert '"passing_yards_per_game":sum(' in s and '"rushing_yards_per_game":sum(' in s
        # Use the available metric adjustment calibration fallback for newly introduced variables.
        # No independent out-of-sample coefficient fitting is asserted.
    filename=ROOT/('_volume_'+label+'_runtime.py')
    filename.write_text(s)
    try:subprocess.run([sys.executable,str(filename)],env=dict(os.environ,MODEL_WEEK='7'),check=True,timeout=1300)
    finally:filename.unlink(missing_ok=True)
    return json.loads((ROOT/'data'/'experiments'/('volume_'+label+'_75_15_10_2026_week_7.json')).read_text())

baseline=run('baseline',False)
enhanced=run('enhanced',True)
a={x['team']:x for x in baseline['rankings']}
b={x['team']:x for x in enhanced['rankings']}
teams=sorted(a,key=lambda t:a[t]['rank'])
rows=[]
for t in teams:
    x=a[t];y=b[t]
    rows.append({'team':t,'baseline_rank':x['rank'],'enhanced_rank':y['rank'],
      'rank_change':x['rank']-y['rank'],
      'baseline_offense':x['offense_rank'],'enhanced_offense':y['offense_rank'],
      'baseline_defense':x['defense_rank'],'enhanced_defense':y['defense_rank'],
      'baseline_sd':x['overall_team_strength_sd'],'enhanced_sd':y['overall_team_strength_sd']})
rank_moves=sorted(rows,key=lambda r:abs(r['rank_change']),reverse=True)
focus=['Georgia','Texas','Ohio State','Oklahoma','Alabama','Miami','Notre Dame','Utah']
report={
 'study':'Frozen-pregame v15 75/15/10 model with passing and rushing yards/game added inside original 18% and 17% category budgets',
 'through_week':6,
 'status':'completed research, not published',
 'data':'CFBD game advanced and play-by-play; same weeks and exclusions across variants',
 'baseline_category_weights':{'scoring':.22,'efficiency':.23,'passing':.18,'rushing':.17,'line':.10,'finishing':.10},
 'new_metrics':['passing_yards_per_game','rushing_yards_per_game'],
 'defensive_treatment':'opponent gained yards become the corresponding negative defensive evidence',
 'limitation':'Yards come from recorded pass/rush play-type yardsGained, so may differ from official net passing/rushing totals; scaling uses full sample through Week 6; early pregames depend on preseason prior; new metric opponent coefficient is default 0.20, not independently calibrated; results are descriptive, not a prospective predictive validation.',
 'baseline_top25': [r['team'] for r in baseline['rankings'][:25]],
 'enhanced_top25':[r['team'] for r in enhanced['rankings'][:25]],
 'focus':[next(r for r in rows if r['team']==t) for t in focus],
 'largest_changes':rank_moves[:30],
 'rankings':rows
}
out=ROOT/target
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'ok','focus':report['focus'],'largest_changes':report['largest_changes'][:15]},indent=2))
