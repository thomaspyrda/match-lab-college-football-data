#!/usr/bin/env python3
"""Freeze verified MLB final regular-season metrics and postseason outcomes."""
import argparse,json,urllib.request
from collections import defaultdict,Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from backfill_mlb_team_metrics import TEAM_IDS,fetch_group,metrics_for
ROOT=Path(__file__).resolve().parent
BASE='https://statsapi.mlb.com/api/v1'
def fetch(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'BetWiseResearch/1.0'}),timeout=60) as r:return json.load(r)
def outcomes(doc):
 games={g['gamePk']:g for day in doc.get('dates',[]) for g in day['games'] if g.get('gameType') in 'FDLW' and g['status']['abstractGameState']=='Final'}
 finals=[g for g in games.values() if g['gameType']=='W' and g.get('seriesStatus',{}).get('isOver')]
 if not finals:return None
 series=defaultdict(list)
 for g in games.values():series[(g['gameType'],tuple(sorted(g['teams'][s]['team']['id'] for s in ['home','away'])))].append(g)
 result={slug:{'status':'missed_playoffs','text':'Missed Playoffs'} for slug in TEAM_IDS.values()}
 labels={'F':'Wild Card Series','D':'Division Series','L':'League Championship Series','W':'World Series'}
 for kind in 'FDLW':
  for (phase,ids),entries in series.items():
   if phase!=kind:continue
   final=max(entries,key=lambda g:g['gameDate']);state=final.get('seriesStatus',{})
   if not state.get('isOver'):raise ValueError('Incomplete playoff series')
   winner,loser=state['winningTeam']['id'],state['losingTeam']['id'];wins=Counter()
   for g in entries:
    home,away=g['teams']['home'],g['teams']['away']
    assert home['score']!=away['score']
    wins[home['team']['id'] if home['score']>away['score'] else away['team']['id']]+=1
   assert (wins[winner],wins[loser])==(state['wins'],state['losses'])
   opponent=state['winningTeam']['name'];score=f'{wins[loser]}–{wins[winner]}'
   result[TEAM_IDS[loser]]={'status':'eliminated','text':f'Lost to {opponent} in {labels[kind]}, {score}','round':labels[kind],'opponent':TEAM_IDS[winner],'series':score}
   if kind=='W':result[TEAM_IDS[winner]]={'status':'champion','text':f'World Series Champions · Defeated {state["losingTeam"]["name"]}, {wins[winner]}–{wins[loser]}','round':'World Series','opponent':TEAM_IDS[loser],'series':f'{wins[winner]}–{wins[loser]}'}
 assert sum(r['status']=='champion' for r in result.values())==1
 assert sum(r['status']=='eliminated' for r in result.values())==11
 assert len(result)==30
 return result

def finalize(year,post=None,standings=None):
 path=ROOT/'data/mlb/season-snapshots.json';snapshot=json.loads(path.read_text());year=str(year)
 if year in snapshot.get('finalized_seasons',{}):print('Preserving finalized MLB season',year);return
 post_url=BASE+f'/schedule?sportId=1&season={year}&gameTypes=F,D,L,W&hydrate=seriesStatus'
 result=outcomes(post or fetch(post_url))
 if not result:print('World Series is not complete; retaining existing season publication');return
 standings_url=BASE+f'/standings?leagueId=103,104&season={year}&standingsTypes=regularSeason'
 table=standings or fetch(standings_url);records={r['team']['id']:r for group in table['records'] for r in group['teamRecords']}
 assert set(records)==set(TEAM_IDS)
 with ThreadPoolExecutor(max_workers=3) as pool:
  futures=[pool.submit(fetch_group,int(year),'hitting'),pool.submit(fetch_group,int(year),'pitching'),pool.submit(fetch_group,int(year),'pitching','rel')]
  (hit,hiturl),(pitch,pitchurl),(bull,bullurl)=[f.result() for f in futures]
 assert all(set(group)==set(TEAM_IDS) for group in [hit,pitch,bull])
 now=datetime.now(timezone.utc).isoformat()
 for tid,slug in TEAM_IDS.items():
  source=records[tid];row=snapshot['seasons'][year][slug];gp=source['gamesPlayed'];assert gp==source['wins']+source['losses']
  row.update(status='complete',games_played=gp,wins=source['wins'],losses=source['losses'],ties=0,runs_scored=source['runsScored'],runs_allowed=source['runsAllowed'],runs_per_game=round(source['runsScored']/gp,1),runs_allowed_per_game=round(source['runsAllowed']/gp,1),source=standings_url)
  splits={r['type']:r for r in source['records']['splitRecords']}
  for site in ['home','away']:row[site]={'wins':splits[site]['wins'],'losses':splits[site]['losses'],'ties':0}
  assert sum(row[site]['wins']+row[site]['losses'] for site in ['home','away'])==gp
  row.update(team_stats=metrics_for(hit[tid],pitch[tid],bull[tid]),team_stats_updated_at=now,team_stats_source={'hitting':hiturl,'pitching':pitchurl,'bullpen':bullurl})
 snapshot.setdefault('finalized_seasons',{})[year]={'finalized_at':now,'source':post_url,'status':'complete'}
 snapshot['generated_at']=now
 playoffpath=ROOT/'data/mlb/season-playoff-results.json';playoffs=json.loads(playoffpath.read_text())
 for slug,row in result.items():playoffs['teams'].setdefault(slug,{})[year]={**row,'source':post_url}
 playoffs['years']='2015–'+year
 if post_url not in playoffs['source_urls']:playoffs['source_urls'].append(post_url)
 playoffs['source']='SABR Lahman historical results; MLB Stats API final postseason series'
 playoffpath.write_text(json.dumps(playoffs,separators=(',',':'),ensure_ascii=False)+'\n')
 path.write_text(json.dumps(snapshot,separators=(',',':'),ensure_ascii=False)+'\n')
 print('Finalized',year,': 30 regular-season teams, all metrics, 30 postseason outcomes')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--year',type=int,default=datetime.now(timezone.utc).year);p.add_argument('--postseason-file',type=Path);p.add_argument('--standings-file',type=Path);a=p.parse_args();finalize(a.year,json.loads(a.postseason_file.read_text()) if a.postseason_file else None,json.loads(a.standings_file.read_text()) if a.standings_file else None)
