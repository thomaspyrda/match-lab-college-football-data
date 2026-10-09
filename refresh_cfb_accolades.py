"""Build sourced program honors from NCAA record books and CFBD bowl supplements."""
import argparse, collections, hashlib, json, re, unicodedata, urllib.request
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE='https://s3.amazonaws.com/fs.ncaa.org/Docs/stats/football_records/'
ALIASES={'southern california':'USC','miami fl':'Miami','army west point':'Army','ole miss':'Mississippi','uconn':'Connecticut','appalachian state':'App State','fla atlantic':'Florida Atlantic','fiu':'Florida International','utsa':'Texas-San Antonio','niu':'Northern Illinois','middle tenn':'Middle Tennessee','southern mississippi':'Southern Miss','southern miss':'Southern Miss','ulm':'UL Monroe','louisiana monroe':'UL Monroe','hawaii':"Hawai'i",'ga southern':'Georgia Southern','ga state':'Georgia State','miami':'Miami (OH)','north carolina state':'NC State','coastal caro':'Coastal Carolina','jacksonville':'Jacksonville State','southwest mo state':'Missouri State','southwest missouri state':'Missouri State','southwest texas state':'Texas State'}
def norm(s):
 s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
 s=re.sub(r'\bst\.?\b','state',s);s=re.sub(r'\bmich\.?\b','michigan',s);s=re.sub(r'\bky\.?\b','kentucky',s)
 return re.sub(r'[^a-z0-9]+',' ',s).strip()
def resolver(teams):
 names={norm(t['name']):str(t['id']) for t in teams}
 for k,v in ALIASES.items():names[norm(k)]=names[norm(v)]
 return lambda s:names.get(norm(s))
def columns(path,start,end,two_until=0,two=False):
 import pdfplumber
 with pdfplumber.open(path) as pdf:
  for i in range(start,end):
   bounds=[(32,308),(310,584)] if two or i<two_until else [(32,216),(218,400),(402,584)]
   for col,(a,b) in enumerate(bounds):
    p=pdf.pages[i].filter(lambda o:a<=o.get('x0',0)<b and 40<=o.get('top',0)<755)
    yield i+1,col+1,p.extract_text(x_tolerance=1.8) or ''
def awards(cols,resolve):
 # Explicit headings prevent coaches, finalists and All-America selections entering player awards.
 headings={'HEISMAN MEMORIAL TROPHY':'Heisman Trophy','MAXWELL AWARD':'Maxwell Award','AP PLAYER OF THE':'AP Player of the Year','JOHN OUTLAND':'Outland Trophy','WALTER CAMP':'Walter Camp Award','VINCE LOMBARDI/':'Lombardi Award','DAVEY O’BRIEN NATIONAL':"Davey O’Brien Award",'DICK BUTKUS':'Butkus Award','JIM THORPE AWARD':'Jim Thorpe Award','JOHNNY UNITAS':'Johnny Unitas Golden Arm Award','DOAK WALKER NATIONAL':'Doak Walker Award','LOU GROZA COLLEGIATE':'Lou Groza Award','BRONKO NAGURSKI':'Bronko Nagurski Trophy','FRED BILETNIKOFF':'Biletnikoff Award','CHUCK BEDNARIK':'Chuck Bednarik Award','RAY GUY PUNTING':'Ray Guy Award','JOHN MACKEY':'John Mackey Award','DAVE RIMINGTON':'Rimington Trophy','LOTT IMPACT':'Lott IMPACT Trophy','MANNING AWARD':'Manning Award','WUERFFEL TROPHY':'Wuerffel Trophy','WILLIAM V.':'William V. Campbell Trophy','BOBBY BOWDEN':'Bobby Bowden Award','RUDY AWARD':'Rudy Award','MOSI TATUPU SPECIAL':'Mosi Tatupu Award','WALTER PAYTON':'Walter Payton Award (FCS)','BUCK BUCHANAN':'Buck Buchanan Award (FCS)','JERRY RICE AWARD':'Jerry Rice Award (FCS)','TED HENDRICKS':'Ted Hendricks Award'}
 current=None;year=None;out=[];unmatched=[]
 for page,col,text in cols:
  for line in text.splitlines():
   if line in headings:current=headings[line];year=None;continue
   if line=='AWARD (FCS)':current='Rimington Award (FCS)'
   if line=='AWARD (NCAA II)':current='Rimington Award (Division II)'
   if line=='AWARD (NCAA III)':current='Rimington Award (Division III)'
   if line.startswith('HARLON HILL') or line=='GENE UPSHAW' or line=='CLIFF MELBERGER':current=None
   if line.startswith('MAYO CLINIC'):current=None
   if not current:continue
   m=re.match(r'^(\d{4})\s+(.+)$',line)
   if m:year=int(m[1]);rest=m[2]
   elif current=='Heisman Trophy':
    if year==2025 and line.startswith('1. '):rest='Fernando Mendoza, Indiana, QB'
    else:continue
   elif year and ',' in line and not re.match(r'^(?:\d(?:nd|rd|th)|Year|\*)[—–]',line):rest=line
   else:continue
   if not 1935<=year<=2025:continue
   parts=rest.split(',');
   if len(parts)<2:continue
   player=parts[0].lstrip('*#').strip();school=re.sub(r'\s+[\d,]+$','',parts[1]).strip()
   tid=resolve(school)
   if tid:out.append({'team_id':tid,'year':year,'award':current,'player':player,'source':'Awards','page':page})
   elif m:unmatched.append((current,year,rest))
 # A player can share an award; preserve each distinct recipient.
 unique={(r['team_id'],r['year'],r['award'],r['player']):r for r in out}
 return list(unique.values()),unmatched

def conferences(cols,resolve):
 current=None;year=None;mode=False;level='FBS';out=[];unmatched=[];all_groups=collections.Counter()
 heads={'American Conference':'American','Atlantic Coast Conference':'ACC','Big 12 Conference':'Big 12','Big East Conference':'Big East','Big Eight Conference':'Big Eight','Big Ten Conference':'Big Ten','Big West Conference':'Big West','Conference USA':'Conference USA','Mid-American Conference':'MAC','Missouri Valley':'Missouri Valley','Mountain States':'Mountain States','Mountain West Conference':'Mountain West','Pac-12 Conference':'Pac-12','Southeastern':'SEC','Southwest Conference':'Southwest','Sun Belt Conference':'Sun Belt','Western Athletic':'WAC','Atlantic 10 Conference':'Atlantic 10','Atlantic Sun-WAC':'ASUN-WAC','Big Sky Conference':'Big Sky','Big South Conference':'Big South','Colonial Athletic':'CAA','Coastal Athletic':'CAA','Great West Conference':'Great West','Missouri Valley Football':'MVFC','Ohio Valley Conference':'Ohio Valley','Southern Conference':'Southern','Southland Conference':'Southland','Southern Intercollegiate':'SIAA','Yankee Conference':'Yankee'}
 for page,col,text in cols:
  for line in text.splitlines():
   if line=='FCS':level='FCS';mode=False
   if line in heads:current=heads[line];mode=False;year=None;continue
   if line.startswith('Year') and 'Champion (Record)' in line:mode=True;continue
   if line.startswith('Year') and 'Championship Game' in line:mode=False;continue
   if not mode or not current:continue
   m=re.match(r'^(\d{4})\s+(.+)$',line)
   if m:year=int(m[1]);rest=m[2]
   elif year and (resolve(line.split(' (')[0]) or re.search(r'\(\d+-\d+',line)):rest=line
   else:continue
   if not 1890<=year<=2025:continue
   name=re.sub(r'\s*\(\d.*','',rest).strip();name=re.sub(r'\s+\d+$','',name)
   tid=resolve(name.lstrip('*#^@'))
   if tid or re.search(r'\(\d[\d-]*\)',rest):all_groups[(year,current)]+=1
   if tid:out.append({'team_id':tid,'year':year,'conference':current,'shared':False,'level':level,'source':'Standings','page':page})
   elif m and '(' in rest:unmatched.append((current,year,rest))
 unique={(r['team_id'],r['year'],r['conference']):r for r in out}
 # The NCAA all-time title totals explicitly exclude these vacated championships.
 vacated={('194',2010,'Big Ten'),('30',2004,'Pac-12'),('30',2005,'Pac-12'),('59',2009,'ACC')}
 for key,r in unique.items():r['vacated']=key in vacated
 counts=all_groups
 # Shared status must include co-champions no longer in the current FBS registry.
 for r in unique.values():r['shared']=counts[(r['year'],r['conference'])]>1
 return list(unique.values()),unmatched

def national_titles(cols,resolve):
 active=False;year=None;pending=None;out=[]
 def flush():
  nonlocal pending
  if pending:
   tid,name,selectors,page,marker=pending
   if tid and year:out.append({'team_id':tid,'year':year,'level':'FBS','selectors':selectors.strip(),'source':'FBS','page':page,'note':'BCS title vacated; AP selection retained' if marker=='#' and year==2004 else ''})
  pending=None
 for page,col,text in cols:
  for line in text.splitlines():
   if line=='FINAL NATIONAL':active=True;continue
   if not active:continue
   if line.startswith('^From 1998') or line.startswith('National Championships'):flush();active=False;continue
   if re.fullmatch(r'\d{4}',line):flush();year=int(line);continue
   m=re.match(r'^([+^#]?)([^:]+):\s*(.*)',line)
   if m:
    flush();pending=[resolve(m[2]),m[2],m[3],page,m[1]]
   elif pending and line and not line.startswith(('#BCS','^From','+Beginning','†Beginning','Note:')):pending[2]+=' '+line
 flush()
 return out

def bowl_wins(cols,resolve):
 bowl=None;out=[];rejected=[]
 for page,col,text in cols:
  lines=text.splitlines()
  for i,line in enumerate(lines):
   # Every game block has a named event directly above its site/name metadata.
   if (line.startswith(('Present Site:','(Montgomery)','(Houston)','(Pasadena)','(San Francisco)','(San Diego)')) and i):
    prior=lines[i-1]
    if prior=='Bowl' and i>1:prior=lines[i-2]+' Bowl'
    if not prior.startswith(('Playing','Stadium','Name','Date','1/')) and not re.match(r'^\d',prior):bowl=prior
   if re.fullmatch(r'\([A-Z][^)]*\)',line) and i and not re.match(r'^\d',lines[i-1]):bowl=lines[i-1]
   if line=='Bowl' and i:bowl=lines[i-1]+' Bowl'
   elif line.endswith('Bowl') and not line.startswith(('Name','Playing')) and len(line)<70:bowl=line
   m=re.match(r'^(\d{1,2})/{1,2}(\d{1,2})/(\d{4})\s+(.+?)\s+(\d+),\s+(.+?)\s+[(*]?(\d+)\b',line)
   if not m:continue
   month,day,calendar=map(int,m.group(1,2,3));winner,score,loser,allowed=m.group(4,5,6,7)
   if int(score)<=int(allowed):continue
   tid=resolve(winner.lstrip('*#^'))
   if not tid:continue
   if not bowl or any(x in bowl.lower() for x in ['championship','first round','all-star']):continue
   year=calendar-1 if month<=3 else calendar
   out.append({'team_id':tid,'year':year,'date':f'{calendar:04d}-{month:02d}-{day:02d}','bowl':bowl,'opponent':loser.lstrip('*#^'),'score':f'{score}–{allowed}','vacated':winner.startswith('*'),'source':'Bowls','page':page})
 return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-dir',default=str(ROOT.parent/'accolades-source'));args=ap.parse_args();source=Path(args.source_dir);source.mkdir(parents=True,exist_ok=True)
 teams=json.loads((ROOT/'data/cfb/team-registry.json').read_text())['teams'];resolve=resolver(teams)
 meta={}
 for name in ['Awards','Standings','Bowls','FBS','FCSchamps']:
  path=source/(name+'.pdf')
  if not path.exists():path.write_bytes(urllib.request.urlopen(SOURCE+name+'.pdf',timeout=60).read())
  meta[name]={'name':'NCAA '+name+' record book','url':SOURCE+name+'.pdf','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 aw,awmiss=awards(columns(source/'Awards.pdf',32,44,two_until=35),resolve)
 cf,cfmiss=conferences(columns(source/'Standings.pdf',15,32),resolve)
 nt=national_titles(columns(source/'FBS.pdf',119,125),resolve)
 claims=json.loads((ROOT/'data/cfb/national-title-claims.json').read_text());meta['Claims']=claims['source']
 selected={(r['team_id'],r['year']):r for r in nt}
 claimed=[]
 for name,years in claims['claims'].items():
  tid=resolve(name)
  if tid:
   for year in years:
    r=dict(selected.get((tid,year),{'team_id':tid,'year':year,'level':'FBS','selectors':'Institutional claim'}));r['claimed']=True;r['source']='Claims';r.pop('page',None);claimed.append(r)
 claim_keys={(r['team_id'],r['year']) for r in claimed}
 for key,r in selected.items():
  if key not in claim_keys:claimed.append(dict(r,claimed=False))
 nt=claimed
 import pdfplumber
 with pdfplumber.open(source/'FCSchamps.pdf') as pdf:
  for index in [3,4]:
   text=pdf.pages[index].filter(lambda o:32<=o.get('x0',0)<139 and 80<=o.get('top',0)<755).extract_text(x_tolerance=1.8) or ''
   for line in text.splitlines():
    m=re.match(r'^(\d{4})\s+(.+)$',line)
    if m and resolve(m[2]):nt.append({'team_id':resolve(m[2]),'year':int(m[1]),'level':'FCS','claimed':True,'selectors':'NCAA Division I championship','source':'FCSchamps','page':index+1})
 bw=bowl_wins(columns(source/'Bowls.pdf',1,19,two=True),resolve)
 # The bowl book currently stops at the 2024 season. Fill newer seasons from our existing completed CFBD detail records.
 book_through=max(r['year'] for r in bw)
 for path in sorted((ROOT/'data/cfb/details').glob('*.json')):
  if int(path.stem)<=book_through:continue
  for g in json.loads(path.read_text()).get('games',[]):
   result=g.get('result');name=g.get('notes') or ''
   if g.get('season_type')!='postseason' or not result or 'bowl' not in name.lower() or 'national championship' in name.lower():continue
   hp,ap=result.get('home_points'),result.get('away_points')
   if hp is None or ap is None or hp==ap:continue
   win,lose=('home','away') if hp>ap else ('away','home');tid=resolve(g[win])
   if tid:bw.append({'team_id':tid,'year':g['season'],'date':g['start_date'][:10],'bowl':name,'opponent':g[lose],'score':f'{max(hp,ap):g}–{min(hp,ap):g}','vacated':False,'source':'CFBD','game_id':g['game_id']})
 meta['CFBD']={'name':'CollegeFootballData postseason games','url':'https://collegefootballdata.com/'}
 output={str(t['id']):{'name':t['name'],'bowl_wins':[],'conference_titles':[],'national_titles':[],'player_awards':[]} for t in teams}
 # Preserve first-round draft data imported from the NFL team-page archive.
 try: previous=json.loads((ROOT/'data/cfb/program-accolades.json').read_text())
 except FileNotFoundError: previous={}
 for k,v in previous.get('sources',{}).items():
  if k.startswith('NFLDraft:'):meta[k]=v
 for tid,team_data in output.items():
  team_data['first_round_draft_picks']=previous.get('teams',{}).get(tid,{}).get('first_round_draft_picks',[])
 for key,rows in [('bowl_wins',bw),('conference_titles',cf),('national_titles',nt),('player_awards',aw)]:
  for r in rows:output[r['team_id']][key].append(r)
  for v in output.values():v[key].sort(key=lambda x:(-x['year'],x.get('award',x.get('bowl',''))))
 assert len(aw)>900 and len(cf)>1200 and len(nt)>150 and len(bw)>1200,(len(aw),len(cf),len(nt),len(bw))
 report={'unmatched_awards':awmiss,'unmatched_conferences':cfmiss}
 (source/'parse-audit.json').write_text(json.dumps(report,indent=2))
 data={'schema_version':1,'updated_at':datetime.now(timezone.utc).isoformat(),'sources':meta,'coverage':{'nfl_first_round_draft_from':previous.get('coverage',{}).get('nfl_first_round_draft_from'),'nfl_first_round_draft_through':previous.get('coverage',{}).get('nfl_first_round_draft_through'),'nfl_first_round_draft_count':previous.get('coverage',{}).get('nfl_first_round_draft_count'),'bowl_book_through':book_through,'bowl_wins_through':max(r['year'] for r in bw),'conference_titles_through':max(r['year'] for r in cf),'national_titles_through':max(r['year'] for r in nt),'player_awards_through':max(r['year'] for r in aw)},'teams':output}
 (ROOT/'data/cfb/program-accolades.json').write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False))
 print('Awards, conference titles, national title selections, bowl wins:',len(aw),len(cf),len(nt),len(bw));print('Coverage',data['coverage'])
if __name__=='__main__':main()
