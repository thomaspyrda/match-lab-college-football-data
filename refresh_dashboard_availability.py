#!/usr/bin/env python3
"""Publish fresh ESPN availability separately from frozen statistical snapshots."""
import json,re,urllib.request
from pathlib import Path
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
PATHS={'nfl':'football/nfl','cfb':'football/college-football','nba':'basketball/nba','cbb':'basketball/mens-college-basketball','mlb':'baseball/mlb'}
ET=ZoneInfo('America/New_York')
def norm(v):return re.sub('[^a-z0-9]','',str(v).lower())
def stamp(v):return datetime.fromisoformat(v.replace('Z','+00:00'))
def get(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'BetWiseResearch/1.0','Accept':'application/json'}),timeout=30) as r:return json.load(r)
def players(rows,now):
 result={};stale=False
 for row in rows:
  athlete=row.get('athlete') or {};name=athlete.get('displayName') or athlete.get('fullName')
  if not name:continue
  detail=row.get('details') or {};reported=row.get('date');ret=detail.get('returnDate')
  try:
   if reported and (stamp(reported)>now+timedelta(minutes=5) or now-stamp(reported)>timedelta(days=365)):
    if not(ret and stamp(ret)>now):stale=True;continue
  except (ValueError,TypeError):stale=True;continue
  reason=[str(detail[k]) for k in ('side','type','detail') if detail.get(k) and str(detail[k]).lower() not in ('other','not specified')]
  status=row.get('status') or (row.get('type') or {}).get('description') or 'Not specified'
  if isinstance(status,dict):status=status.get('description') or status.get('name') or 'Not specified'
  item={'name':name,'position':(athlete.get('position') or {}).get('abbreviation'),'status':status,'reason':' · '.join(reason) or row.get('shortComment') or 'Reason not provided','reported_at':reported}
  result[str(athlete.get('id') or name)]=item
 return sorted(result.values(),key=lambda p:({'out':0,'doubtful':1,'questionable':2,'day-to-day':3,'probable':4}.get(p['status'].lower(),5),p['name'])),stale

class TextOnly(__import__('html.parser',fromlist=['HTMLParser']).HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,data):self.parts.append(data)
def plain(value):
 parser=TextOnly();parser.feed(value);return ' '.join(' '.join(parser.parts).split())
def college_reports(html,sport,now):
 """Read current, public Covers team injury tables; preserve reported statuses."""
 title=re.search(r'<title>(.*?)</title>',html,re.S)
 current=now.astimezone(ET).date()
 if not title or current.strftime('%b')+' '+str(current.day)+', '+str(current.year) not in title[1]:raise ValueError('College injury page does not identify today’s report date')
 import html as html_module,unicodedata
 def key(value):
  value=html_module.unescape(str(value))
  value=unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower()
  value=re.sub(r'\bstate\b','st',value);value=re.sub(r'\bsaint\b','st',value);value=re.sub(r'\buniversity\b','',value)
  return norm(value)
 registry=json.loads((ROOT/'data/sports/team-registry.json').read_text())['teams'];names={}
 for t in registry:
  if t['sport']!='cbb':continue
  for name in [t['name'],t['short_name'],*t.get('aliases',[])]:
   if name:names[key(name)]=str(t['espn_id'])
 if sport=='cfb':
  for t in json.loads((ROOT/'data/cfb/team-registry.json').read_text())['teams']:names[key(t['name'])]=str(t['id'])
 aliases={'UConn':'Connecticut','Connecticut':'UConn','Southern California':'USC','Central Florida':'UCF','Brigham Young':'BYU','Louisiana-Monroe':'UL Monroe','Louisiana-Lafayette':'Louisiana','Texas-El Paso':'UTEP','Texas-San Antonio':'UTSA','Texas-Arlington':'UT Arlington','California-Los Angeles':'UCLA','Nevada-Las Vegas':'UNLV','Southern Methodist':'SMU','Virginia Commonwealth':'VCU','Texas Christian':'TCU','Alabama-Birmingham':'UAB','Pittsburgh':'Pitt','North Carolina State':'NC State','Appalachian State':'App State','Miami Ohio':'Miami OH','Miami (Ohio)':'Miami OH','Miami (OH)':'Miami OH','Miami (FL)':'Miami','St. John\'s':'St John\'s','Saint Francis PA':'St Francis PA','Long Island':'Long Island','SIU-Edwardsville':'SIUE','UMass Lowell':'UMass Lowell'}
 aliases.update({'FIU Panthers':'FIU','JSU':'Jacksonville St','MS State':'Mississippi St','ND State':'North Dakota State','Albany':'UAlbany','American U.':'American','Appalachian St.':'App State','Cal Poly SLO':'Cal Poly','Central CT':'C Connecticut','CSU Bakersfield':'Bakersfield','CSU Fullerton':'Fullerton','Eastern WA':'E Washington','Fort Wayne':'Purdue FW','Illinois-Chicago':'UIC','IUPUI':'IU Indy','Louisiana State':'LSU','Massachusetts':'UMass','Miami-Florida':'Miami','Middle TN':'MTSU','Mississippi':'Ole Miss','Monmouth-NJ':'Monmouth','Northern CO':'N Colorado','Northern KY':'N Kentucky','Northwestern St.':"N'Western St",'Pennsylvania':'Penn','Queens NC':'Queens','San Jose St.':'San José St','San Jose State':'San José St','SD State':'S Dakota St','SE Missouri St.':'SE Missouri','Seattle':'Seattle U','Southern IL':'S Illinois','St. Thomas (MN)':'St Thomas','Tenn-Martin':'UT Martin','Texas R-G Valley':'UT Rio Grande','UL Lafayette':'Louisiana','USC Upstate':'SC Upstate','New Orleans':'LSU N Orleans','Grambling State':'Grambling','McNeese St.':'McNeese','Nebraska Omaha':'Omaha','Nicholls State':'Nicholls','Sam Houston St.':'Sam Houston'})
 for alias,target in aliases.items():
  if key(target) in names:names[key(alias)]=names[key(target)]
 # Match complete team sections instead of navigation links or player detail rows.
 sections=re.findall(r'<a id="([^"]+)"></a>\s*<section>(.*?)</section>',html,re.S)
 if len(sections)<(100 if sport=='cfb' else 300):raise ValueError('College injury tables are incomplete')
 result={};unmapped=[]
 for school,section in sections:
  school=html_module.unescape(school)
  tid=names.get(key(school))
  if not tid:
   hits={str(t['espn_id']) for t in registry if t['sport']=='cbb' and key(t['name']).startswith(key(school))}
   if len(hits)==1:tid=next(iter(hits))
  if not tid:unmapped.append(school);continue
  records=[]
  for attrs,row in re.findall(r'<tr([^>]*)>(.*?)</tr>',section,re.S):
   if 'collapse' in attrs:continue
   cells=re.findall(r'<td[^>]*>(.*?)</td>',row,re.S)
   if len(cells)<3:continue
   name,position=plain(cells[0]),plain(cells[1]);bold=re.search('<b>(.*?)</b>',cells[2],re.S)
   if not name or not bold:continue
   status,sep,reason=plain(bold[1]).partition(' - ')
   records.append({'name':name,'position':position,'status':status,'reason':reason if sep else 'Reason not provided'})
  if not records and 'No injuries to report' not in section:continue
  result[tid]={'state':'reported','checked_at':now.isoformat(),'source':'https://www.covers.com/sport/'+('football/ncaaf' if sport=='cfb' else 'basketball/ncaab')+'/injuries','source_name':'Covers','context':'team_report','name':school,'players':records,'report_as_of':current.isoformat()}
 if unmapped:print(sport,'Unmatched college injury teams:',unmapped,flush=True)
 return result

def collect(sport,now):
 base='https://site.api.espn.com/apis/site/v2/sports/'+PATHS[sport]+'/'
 expected=now.astimezone(ET).year+(sport in ('nba','cbb') and now.astimezone(ET).month>=7)
 output={'sport':sport,'checked_at':now.isoformat(),'source':'ESPN','teams':{},'aliases':{},'matchups':{}}
 def add(tid,name,rows,source,context,asof=None,abbr=None):
  if tid is None or not isinstance(rows,list):return
  parsed,stale=players(rows,now)
  output['teams'][str(tid)]={'state':'unavailable' if stale and not parsed else 'reported','checked_at':now.isoformat(),'source':source,'context':context,'name':name,'players':parsed,'report_as_of':asof}
  for alias in (name,abbr):
   if alias:output['aliases'][norm(alias)]=str(tid)
 try:
  raw=get(base+'injuries?limit=1000');asof=stamp(raw['timestamp'])
  if raw.get('status')=='success' and raw.get('season',{}).get('year')==expected and timedelta(minutes=-5)<=now-asof<=timedelta(hours=30):
   for group in raw.get('injuries',[]):add(group.get('id'),group.get('displayName'),group.get('injuries'),f'https://www.espn.com/{"college-football" if sport=="cfb" else "mens-college-basketball" if sport=="cbb" else sport}/injuries','team_report',raw['timestamp'])
 except Exception as e:output['collection_error']=type(e).__name__
 # Use existing schedules, not historical injury lookups or inferred healthy rosters.
 try:
  path={'nba':'nba/dashboard/data/dashboard.json','cbb':'cbb/dashboard/data/dashboard.json','mlb':'mlb/dashboard/data/dashboard.json','cfb':'cfb-dashboard-preview/data/dashboard.json'}.get(sport)
  if path:dashboard=json.loads((ROOT/path).read_text())
  else:dashboard=get('https://nfl.parlaycalculator.bet/data/dashboard.json')
 except Exception:dashboard={'games':[]}
 games=[]
 if sport=='nfl':
  # ESPN's week scoreboard provides the actual timestamp behind display-only kickoff labels.
  week=dashboard.get('slate',{}).get('week') or dashboard.get('week')
  if not week:
   match=re.search(rf'{expected}[_-](\d+)',str((dashboard.get('games') or [{}])[0].get('id','')));week=int(match[1]) if match else None
  try:
   raw=get(base+'scoreboard'+(f'?dates={expected}&seasontype=2&week={week}' if week else ''))
   for event in raw.get('events',[]):
    comp=event['competitions'][0];sides={r['homeAway']:r['team'] for r in comp.get('competitors',[])}
    if not {'away','home'}<=sides.keys():continue
    for t in sides.values():
     for alias in [t.get('displayName'),t.get('abbreviation')]:
      if alias:output['aliases'][norm(alias)]=str(t['id'])
    output['matchups'][sides['away']['abbreviation']+'|'+sides['home']['abbreviation']]={'date':event['date'],'id':event['id']}
    games.append({'id':event['id'],'date':event['date'],'away':sides['away'],'home':sides['home']})
  except Exception:pass
 else:
  for g in dashboard.get('games',[]):
   sides={side:dashboard.get('teams',{}).get(g[side],{}) if isinstance(g[side],str) else g[side] for side in ('away','home')}
   games.append({'id':g.get('game_id') or g.get('id'),'date':g.get('date') or g.get('kickoff'),**sides})
 jobs=[]
 for g in games:
  try:
   dt=stamp(g['date']);age=dt-now
   if not -timedelta(hours=6)<=age<=timedelta(days=8):continue
  except Exception:continue
  missing=any(output['teams'].get(str(t.get('espn_id') or t.get('id')),{}).get('state')!='reported' for t in (g['away'],g['home']))
  if missing and (sport=='cfb' or age<=timedelta(days=2)):jobs.append(g)
 def summary(g):
  try:
   raw=get(base+'summary?event='+str(g['id']))
   if str(raw.get('header',{}).get('id'))!=str(g['id']) or raw.get('header',{}).get('season',{}).get('year')!=expected:return
   for group in raw.get('injuries',[]):
    t=group.get('team') or {};add(t.get('id'),t.get('displayName') or t.get('name'),group.get('injuries'),f'https://www.espn.com/{"college-football" if sport=="cfb" else "mens-college-basketball" if sport=="cbb" else sport}/game/_/gameId/{g["id"]}','matchup',now.isoformat(),t.get('abbreviation'))
  except Exception:pass
 with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(summary,jobs))
 if sport in ('cfb','cbb'):
  try:
   url='https://www.covers.com/sport/'+('football/ncaaf' if sport=='cfb' else 'basketball/ncaab')+'/injuries'
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'BetWiseResearch/1.0'}),timeout=35) as response:html=response.read().decode()
   sourced=college_reports(html,sport,now)
   for tid,report in sourced.items():
    if output['teams'].get(tid,{}).get('state')!='reported':output['teams'][tid]=report;output['aliases'][norm(report['name'])]=tid
  except Exception as e:output['college_source_error']=str(e)
 target=ROOT/'data/dashboard-availability'/f'{sport}.json' ;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(output,separators=(',',':'),ensure_ascii=False)+'\n')
 print(sport,len(output['teams']),'team reports;',sum(len(r['players']) for r in output['teams'].values()),'players;',len(jobs),'matchup checks',flush=True)
 return output
if __name__=='__main__':
 now=datetime.now(timezone.utc)
 with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda s:collect(s,now),PATHS))
