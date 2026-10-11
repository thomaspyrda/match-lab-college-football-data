#!/usr/bin/env python3
"""Weighted six-category symmetric CSC performance test, research only."""
import json,os,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parent
baseline_script=(root/'run_hybrid_recursive_research.py').read_text()
v15=(root/'experiment_dominance_v15.py').read_text()
start=v15.index('    off_metric={}; def_metric={}')
end=v15.index('    # Persist raw FCS residual diagnostics',start)
block=baseline_script.split("block='''",1)[1].split("'''\nsrc=src[:begin]",1)[0]
src=v15[:start]+block+v15[end:]
src=src.replace('    calibration=json.loads(FCS_CALIBRATION.read_text())','    HYBRID_COEFF=1.0\n    QRR_WEIGHT=0.15\n    calibration=json.loads(FCS_CALIBRATION.read_text())')
old='OUT=ROOT/"data"/"experiments"/f"recursive_unit_strength_v15_{SEASON}_week_{WEEK}.json"'
assert old in src
src=src.replace(old,'OUT=ROOT/"data"/"experiments"/f"hybrid_weighted_symmetric_csc_75_15_10_2026_week_7.json"')
needle='    ro,rd,rt=ranks(off),ranks(deff),ranks(overall)'
assert needle in src
addition='''    # Quality result: actual W/D/L minus expectation implied by existing
    # opponent-adjusted team strength, averaged by team (no margin duplication).
    # Cross-sectional distribution is centered and stabilized with reliability shrinkage.
    import math
    base_overall=overall.copy()
    residuals=defaultdict(list)
    result_games=defaultdict(list)
    for g in games:
        home=canon(g.get("home"));away=canon(g.get("away"))
        if home not in overall or away not in overall:continue
        result=g.get("result") or {}
        hp=result.get("home_points");ap=result.get("away_points")
        if hp is None or ap is None:continue
        hp=float(hp);ap=float(ap)
        actual=1.0 if hp>ap else .5 if hp==ap else 0.0
        # Opponent quality enters via the opposing team's established hybrid strength.
        ex=1/(1+math.exp(-1.2*(base_overall[home]-base_overall[away])))
        # Opponent strength determines significance symmetrically: stronger
        # opponent => greater evidence for a win and for a loss; a weak
        # opponent => smaller win credit but greater penalty for a loss.
        # Opponent strength in FBS SD, bounded multiplicative effect.
        h_opp=max(-2.5,min(2.5,base_overall[away]))
        a_opp=max(-2.5,min(2.5,base_overall[home]))
        h_factor=max(.50,min(2.50,math.exp(.35*h_opp))) if actual>=.5 else max(.50,min(2.50,math.exp(-.35*h_opp)))
        a_factor=max(.50,min(2.50,math.exp(.35*a_opp))) if actual<=.5 else max(.50,min(2.50,math.exp(-.35*a_opp)))
        residuals[home].append((actual-ex)*h_factor)
        residuals[away].append(((1-actual)-(1-ex))*a_factor)
        result_games[home].append((away,hp,ap,round(ex,4)))
        result_games[away].append((home,ap,hp,round(1-ex,4)))
    raw_qrr={t:(sum(residuals[t])/(len(residuals[t])+4) if residuals[t] else 0.0) for t in teams}
    qrr=zdict(raw_qrr)
    # Symmetric performance + result interaction: compare per-game metric
    # evidence to the FBS-adjusted expected performance against each unit.
    # Positive or negative extremes have identical strength scaling and caps.
    # Use exactly the six v15 category weights and the 50/50 O/D split.
    # Offensive game evidence is adjusted by faced defensive composite;
    # defensive game evidence is adjusted by faced offensive composite.
    # A category averages its *available* metrics, then categories are
    # combined using the existing CATS weights and renormalized for coverage.
    def game_category_strength(own_row, opponent_unit, defensive=False):
        category_parts=[]
        for cat,(weight,metrics) in CATS.items():
            terms=[]
            for m in metrics:
                if own_row[m] is None: continue
                raw=(own_row[m]-mus[m])/sds[m]
                signed=-raw if defensive else raw
                coefficient=mult_calibration["metrics"].get(m,{}).get("selected_coefficient",0.20)
                terms.append(adjusted_evidence(signed,opponent_unit,coefficient))
            if terms:category_parts.append((weight,sum(terms)/len(terms)))
        den=sum(w for w,_ in category_parts)
        return sum(w*v for w,v in category_parts)/den if den else None
    metric_signal={}
    game_units={}
    for h,a,hm,am in obs:
        for t,o,own,opp in ((h,a,hm,am),(a,h,am,hm)):
            offense_game=game_category_strength(own,comp_def.get(o,0.0))
            defense_game=game_category_strength(opp,comp_off.get(o,0.0),defensive=True)
            if offense_game is None and defense_game is None: continue
            if offense_game is None: performance=defense_game
            elif defense_game is None: performance=offense_game
            else: performance=.5*offense_game+.5*defense_game
            metric_signal[(t,o)]=performance
            game_units[(t,o)]=(offense_game,defense_game)
    competitive=defaultdict(list);competitive_games=defaultdict(list)
    for t,results in result_games.items():
        for opponent,pf,pa,expected in results:
            # Signed quality axis for symmetric positive/negative evidence.
            # A stronger opponent raises the reward for overachievement; a
            # weaker opponent raises the penalty for underachievement.
            opp_sd=max(-2.5,min(2.5,base_overall[opponent]))
            result=(1.0 if pf>pa else .5 if pf==pa else 0.0)
            surprise=result-expected
            perf=metric_signal.get((t,opponent),0.0)
            # Explicit mirror: strength S, statistical signal P and result R
            # have equal/opposite effect under (S,P,R)->(-S,-P,-R).
            # Merely facing a difficult opponent earns nothing.
            p=math.tanh(perf)
            strong=max(0.0,opp_sd)
            weak=max(0.0,-opp_sd)
            pos_performance=strong*max(0.0,p)
            neg_performance=weak*max(0.0,-p)
            pos_result=strong*max(0.0,surprise)
            neg_result=weak*max(0.0,-surprise)
            pos_interaction=strong*max(0.0,p)*max(0.0,surprise)
            neg_interaction=weak*max(0.0,-p)*max(0.0,-surprise)
            value=0.40*((pos_performance-neg_performance)+(pos_result-neg_result)+(pos_interaction-neg_interaction))
            value=max(-2.0,min(2.0,value))
            competitive[t].append(value)
            competitive_games[t].append({"opponent":opponent,"own_points":pf,"opp_points":pa,"opponent_sd":round(opp_sd,3),"performance_signal":round(perf,4),"offensive_game_signal":round(game_units.get((t,opponent),(None,None))[0],4) if game_units.get((t,opponent),(None,None))[0] is not None else None,"defensive_game_signal":round(game_units.get((t,opponent),(None,None))[1],4) if game_units.get((t,opponent),(None,None))[1] is not None else None,"result_surprise":round(surprise,4),"credit":round(value,4)})
    csc_raw={t:(sum(competitive[t])/(len(competitive[t])+4) if competitive[t] else 0.0) for t in teams}
    csc=zdict(csc_raw)
    overall=zdict({t:.75*base_overall[t]+.15*qrr[t]+.10*csc[t] for t in teams})
    csc_details={t:{"raw":round(csc_raw[t],5),"sd":round(csc[t],4),"games":competitive_games[t]} for t in teams}
    qrr_details={t:{"games":len(residuals[t]),"wins":sum(1 for x in result_games[t] if x[1]>x[2]),"losses":sum(1 for x in result_games[t] if x[1]<x[2]),"raw_result_surprise":round(raw_qrr[t],5),"qrr_sd":round(qrr[t],4),"baseline_rank":ranks(base_overall)[t],"baseline_sd":round(base_overall[t],4)} for t in teams}
'''
src=src.replace(needle,addition+needle)
src=src.replace('"convergence":convergence,"fcs_diagnostics":fcs_diagnostics,"rankings":rows}', '"convergence":convergence,"fcs_diagnostics":fcs_diagnostics,"competitive_strength_credit":{"weight":0.10,"method":"Symmetric CSC using v15 CATS category weights and 50/50 game offense-defense combined opponent-adjusted metric evidence; bounded and FBS centered","details":csc_details},"quality_results":{"weight":QRR_WEIGHT,"definition":"Opponent-strength-adjusted W/L residual over baseline hybrid expected result with 4-game reliability shrinkage; baseline logistic slope 1.2 is a sensitivity assumption, not validated","diagnostics":qrr_details},"rankings":rows}')
# insert a frozen pregame profile into the generated runtime before recursion
pregame="    # Frozen pregame opponent unit profiles from available prior matchups.\n    pregame_off={};pregame_def={};pregame_strength={}\n    past_off=defaultdict(list);past_def=defaultdict(list)\n    def game_raw_unit(row,defensive=False):\n        parts=[]\n        for cat,(w,ms) in CATS.items():\n            vals=[(-1.0 if defensive else 1.0)*(row[m]-mus[m])/sds[m] for m in ms if row[m] is not None]\n            if vals:parts.append((w,sum(vals)/len(vals)))\n        den=sum(w for w,v in parts)\n        return sum(w*v for w,v in parts)/den if den else None\n    for home,away,home_m,away_m in obs:\n        def pre(t,unit):\n            history=past_off[t] if unit=='off' else past_def[t]\n            p=evidence_prior_weight(len(history))\n            return p*prior_z.get(t,0.0)+(1-p)*(sum(history)/len(history) if history else prior_z.get(t,0.0))\n        ho,hd,ao,ad=pre(home,'off'),pre(home,'def'),pre(away,'off'),pre(away,'def')\n        pregame_off[(home,away)],pregame_def[(home,away)],pregame_strength[(home,away)]=ho,hd,.5*(ho+hd)\n        pregame_off[(away,home)],pregame_def[(away,home)],pregame_strength[(away,home)]=ao,ad,.5*(ao+ad)\n        for t,own,opp in ((home,home_m,away_m),(away,away_m,home_m)):\n            x=game_raw_unit(own);y=game_raw_unit(opp,True)\n            if x is not None:past_off[t].append(x)\n            if y is not None:past_def[t].append(y)\n"
src=src.replace('    game_metric={} ', '    game_metric={} ') # compatibility no-op
anchor='    game_metric={}'
assert anchor in src
src=src.replace(anchor,pregame+anchor)
variants=[]
for label,coeff,temporal in [('pregame',1.0,True),('raw',0.0,False)]:
 variant=src.replace('hybrid_weighted_symmetric_csc_75_15_10_2026_week_7.json',f'comparison_{label}_75_15_10_2026_week_7.json')
 variant=variant.replace('    HYBRID_COEFF=1.0','    HYBRID_COEFF='+str(coeff))
 if temporal:
  variant=variant.replace('adjusted_evidence(z,comp_def.get(o,0),sens)','adjusted_evidence(z,pregame_def.get((t,o),0),sens)')
  variant=variant.replace('adjusted_evidence(-z,comp_off.get(o,0),sens)','adjusted_evidence(-z,pregame_off.get((t,o),0),sens)')
  variant=variant.replace('game_category_strength(own,comp_def.get(o,0.0))','game_category_strength(own,pregame_def.get((t,o),0.0))')
  variant=variant.replace('game_category_strength(opp,comp_off.get(o,0.0),defensive=True)','game_category_strength(opp,pregame_off.get((t,o),0.0),defensive=True)')
  variant=variant.replace('opp_sd=max(-2.5,min(2.5,base_overall[opponent]))','opp_sd=max(-2.5,min(2.5,pregame_strength.get((opponent,t),0.0)))')
  variant=variant.replace('ex=1/(1+math.exp(-1.2*(base_overall[home]-base_overall[away])))','ex=1/(1+math.exp(-1.2*(pregame_strength.get((home,away),0.0)-pregame_strength.get((away,home),0.0))))')
  variant=variant.replace('h_opp=max(-2.5,min(2.5,base_overall[away]))','h_opp=max(-2.5,min(2.5,pregame_strength.get((away,home),0.0)))')
  variant=variant.replace('a_opp=max(-2.5,min(2.5,base_overall[home]))','a_opp=max(-2.5,min(2.5,pregame_strength.get((home,away),0.0)))')
 else:
  variant=variant.replace('game_category_strength(own,comp_def.get(o,0.0))','game_category_strength(own,0.0)')
  variant=variant.replace('game_category_strength(opp,comp_off.get(o,0.0),defensive=True)','game_category_strength(opp,0.0,defensive=True)')
  # Keep QRR/CSC opponent assessment fixed at pregame levels as a control;
  # only statistical performance removes opponent adjustment.
  variant=variant.replace('opp_sd=max(-2.5,min(2.5,base_overall[opponent]))','opp_sd=max(-2.5,min(2.5,pregame_strength.get((opponent,t),0.0)))')
 p=root/f'_temporal_{label}_runtime.py'
 p.write_text(variant)
 try:
  subprocess.run([sys.executable,str(p)],env=dict(os.environ,MODEL_WEEK='7'),check=True,timeout=800)
 finally:p.unlink(missing_ok=True)
 variants.append((label,json.loads((root/f'data/experiments/comparison_{label}_75_15_10_2026_week_7.json').read_text())))
current=json.loads((root/'data/experiments/hybrid_weighted_symmetric_csc_75_15_10_2026_week_7.json').read_text())
models=[('recursive',current)]+variants
focus=['Georgia','Texas','Kentucky','Alabama','Ohio State','Oklahoma','Miami','Notre Dame','Utah']
report={'study':'Current recursive versus frozen pregame opponent strength versus raw statistical adjustments','through_week':6,'production_unchanged':True,'important_limitations':['Pregame profiles use completed earlier matchups and preseason priors; shared scaling and metric denominators are estimated from through-Week-6 data and are not strict leakage-free','Raw statistical control removes opponent correction from the 75% statistical component but retains pregame opponent context in the 15% QRR and 10% CSC','Pregame ratings are frozen for each matchup, while recursive final rankings recompute through Week 6','Early-season games lean heavily on preseason assessments'],'models':[],'focus':[]}
for name,d in models:
 rr={r['team']:r for r in d['rankings']}
 report['models'].append({'model':name,'top25':[{'rank':r['rank'],'team':r['team']} for r in d['rankings'][:25]]})
 report['focus'].append({'model':name,'teams':[{'team':t,'rank':rr[t]['rank'],'offense_rank':rr[t]['offense_rank'],'defense_rank':rr[t]['defense_rank'],'off_sd':rr[t]['offensive_strength_sd'],'def_sd':rr[t]['defensive_strength_sd'],'overall_sd':rr[t]['overall_team_strength_sd'],'csc_sd':d['competitive_strength_credit']['details'][t]['sd']} for t in focus]})
(root/'data/experiments/temporal_opponent_strength_comparison_2026.json').write_text(json.dumps(report,indent=2)+chr(10))
print(json.dumps({'models':report['models'],'focus':report['focus']},indent=2))
