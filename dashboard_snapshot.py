"""Compact shared team identity and metric definitions for dashboard delivery."""
def compact(data):
 teams={};definitions={};games=[]
 for game in data['games']:
  item=dict(game)
  for side in ['away','home']:
   t=game[side];teams[t['id']]=t;item[side]=t['id']
  metrics=[]
  for m in game['metrics']:
   definitions[m['key']]={k:v for k,v in m.items() if k not in ['away','home']}
   metrics.append({k:v for k,v in m.items() if k in ['key','away','home'] and v is not None})
  item['metrics']=metrics;games.append(item)
 return dict(data,schema_version=2,teams=teams,metric_definitions=definitions,games=games)
