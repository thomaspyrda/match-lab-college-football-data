"""Aggregate documented NCAA detailed box scores; retain sample coverage."""
import csv,json,argparse
from pathlib import Path
from collections import defaultdict
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,required=True);a=p.parse_args()
registry={t['slug'] for t in json.loads((R/'data/sports/team-registry.json').read_text())['teams'] if t['sport']=='cbb'}
mapping={k:v['slug'] for k,v in json.loads((R/'data/cbb/tournament-team-map.json').read_text())['teams'].items() if v.get('slug') in registry};mapping.update({'1237':'iu-indianapolis-jaguars','1477':'east-texas-am-lions'})
acc=defaultdict(lambda:defaultdict(float))
for row in csv.DictReader((a.source_dir/'MRegularSeasonDetailedResults.csv').open()):
 if not 2016<=int(row['Season'])<=2026:continue
 for own,opp in [('W','L'),('L','W')]:
  slug=mapping.get(row[own+'TeamID'])
  if not slug:continue
  t=acc[row['Season'],slug];t['games']+=1
  for key in ['FGM','FGA','FGM3','FGA3','FTM','FTA','OR','DR','Ast','TO','Stl','Blk','Score']:
   t[key]+=float(row[own+key]);t['opp'+key]+=float(row[opp+key])
seasons=defaultdict(dict)
for (y,s),t in acc.items():
 div=lambda x,z:100*t[x]/t[z] if t[z] else None
 g=t['games'];reb=t['OR']+t['DR'];oreb=t['oppOR']+t['oppDR']
 values={'FG% Allowed':div('oppFGM','oppFGA'),'eFG% Allowed':100*(t['oppFGM']+.5*t['oppFGM3'])/t['oppFGA'] if t['oppFGA'] else None,'3P% Allowed':div('oppFGM3','oppFGA3'),'3P Rate Allowed':div('oppFGA3','oppFGA'),'FT% Allowed':div('oppFTM','oppFTA'),'FT Attempt Rate Allowed':div('oppFTA','oppFGA'),'Rebounds Allowed/Game':oreb/g,'Total Rebound Rate':100*reb/(reb+oreb) if reb+oreb else None,'Defensive Rebound Rate':100*t['DR']/(t['DR']+t['oppOR']) if t['DR']+t['oppOR'] else None,'AST/G Allowed':t['oppAst']/g,'Turnover Margin':(t['oppTO']-t['TO'])/g}
 seasons[y][s]={'values':values,'games':int(g),'sample':'Division I opponent box scores; regular season including conference tournaments','ranks':{}}
for y,teams in seasons.items():
 for key in next(iter(teams.values()))['values']:
  items=[(s,d['values'][key]) for s,d in teams.items() if d['values'][key] is not None];items.sort(key=lambda x:x[1],reverse=key in ['Total Rebound Rate','Defensive Rebound Rate','Turnover Margin'])
  last=None;rank=0
  for i,(s,v) in enumerate(items):
   if v!=last:rank=i+1
   teams[s]['ranks'][key]={'rank':rank,'size':len(items)};last=v
out={'source':'https://github.com/KernelMcGregor/2026MMMLM/tree/main/Data','seasons':seasons}
(R/'data/cbb/opponent-metrics.json').write_text(json.dumps(out,separators=(',',':'))+'\n')
print('Opponent metrics populated',len(acc),'team seasons')
