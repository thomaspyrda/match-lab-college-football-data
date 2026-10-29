"""Remove predictive ESPN entries and restore summaries from verified markets."""
import json,subprocess
from collections import Counter,defaultdict
import recover_cbb_historical_markets as m
BASELINE='976624ebacd97160be5066b72a4fafbcc2170d99'
archives,markets,games,_=m.context();changed=set();removed=Counter()
for s,d in markets.items():
 for y,rows in d.get('games',{}).items():
  for gid,v in rows.items():
   for k,field in [('ats','spread'),('ou','total')]:
    if 'sports.core.api.espn.com' not in v.get(k+'_source',''):continue
    provider=v.get(k+'_provider','').lower()
    if not any(x in provider for x in ['accuscore','numberfire','prediction','predictor','live odds','in-play','inplay']):continue
    for key in [field,k,k+'_provider',k+'_source']:v.pop(key,None)
    v.get('market_line_types',{}).pop(k,None);removed[provider+'_'+k]+=1;changed.add((s,y))
for s,y in changed:
 baseline=json.loads(subprocess.check_output(['git','show',f'{BASELINE}:data/cbb/markets/{s}.json']))
 old=baseline.get('seasons',{}).get(y)
 if old:markets[s].setdefault('seasons',{})[y]=old
 else:markets[s].get('seasons',{}).pop(y,None)
 ats=[0,0,0];ou=[0,0,0];seen=set()
 for phase in archives[s]['seasons'][y].get('phases',{}).values():
  for g in phase.get('games',[]):
   gid=str(g['id'])
   if not m.played(g) or gid in seen:continue
   seen.add(gid);v={**g,**markets[s]['games'].get(y,{}).get(gid,{})}
   if m.has(v,'ats'):ats[['W','L','P'].index(v.get('ats') or v.get('ats_result'))]+=1
   if m.has(v,'ou'):ou[['O','U','P'].index(v.get('ou') or v.get('ou_result'))]+=1
 rec={'ats':ats,'ou':ou,'expected_games':len(seen),'source':'https://github.com/thomaspyrda/match-lab-college-football-data/blob/main/data/cbb/historical-market-recovery-report.json','coverage':'Verified archived market lines; prediction providers excluded; unlined games excluded'}
 markets[s].setdefault('verified_game_seasons',{})[y]=rec
 if not old or sum(ats)>=sum(old['ats']) and sum(ou)>=sum(old['ou']) and (sum(ats)>sum(old['ats']) or sum(ou)>sum(old['ou'])):markets[s].setdefault('seasons',{})[y]=rec
for s in {s for s,y in changed}:m.save(m.R/f'data/cbb/markets/{s}.json',markets[s])
_,markets,_,remaining=m.context();source_games=defaultdict(set);counts=Counter()
for d in markets.values():
 for y,rows in d.get('games',{}).items():
  for gid,v in rows.items():
   for k in ['ats','ou']:
    source=v.get(k+'_source','')
    if 'sports.core.api.espn.com' in source or 'DillonKoch/Sports_Betting' in source:
     source_games['any'].add(gid);source_games[k].add(gid);counts[k+'_team_rows']+=1
p=m.R/'data/cbb/historical-market-recovery-report.json';report=m.read(p)
for entry in report.get('passes',[]):
 if entry.get('source','').startswith('ESPN') and not entry.get('excluded_prediction_providers'):entry['superseded_by_prediction_provider_audit']=True
if removed:report.setdefault('provider_exclusion_audits',[]).append(dict(removed))
all_removed=Counter()
for audit in report.get('provider_exclusion_audits',[]):all_removed.update(audit)
report['verified_recovery_summary']={'initial_target_games':4403,'remaining_incomplete_games':len(remaining),'fully_recovered_games':4403-len(remaining),'games_with_at_least_one_added_market':len(source_games['any']),'games_with_added_ats':len(source_games['ats']),'games_with_added_ou':len(source_games['ou']),'team_row_counts':dict(counts),'removed_nonmarket_entries':dict(all_removed),'method':'Only archived market lines; AccuScore, numberFire and prediction providers excluded'}
m.save(p,report);print(json.dumps(report['verified_recovery_summary']))
