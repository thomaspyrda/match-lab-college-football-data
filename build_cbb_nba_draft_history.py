#!/usr/bin/env python3
"""Build all-round college draft histories from official NBA DraftHistory (1947 onward)."""
import argparse,json,re,unicodedata,urllib.request
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE='https://stats.nba.com/stats/drafthistory?LeagueID=00&College=&OverallPick=&RoundNum=&RoundPick=&Season=&TeamID=0&TopX=&Weight='
def norm(s):
 s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower().replace('&','and')
 s=re.sub(r'\b(university|college|the|of|at)\b','',s)
 return re.sub('[^a-z0-9]','',s.replace('saint','st').replace('state','st'))
# Explicit NBA organization labels for renamed institutions and common abbreviations.
ALIASES={
 'California-Los Angeles':'ucla-bruins','North Carolina State':'nc-state-wolfpack',"St. John's (NY)":'st-johns-red-storm',
 'Southern California':'usc-trojans','Louisiana State':'lsu-tigers','Connecticut':'uconn-huskies','Nevada-Las Vegas':'unlv-rebels','Brigham Young':'byu-cougars',
 'Western Kentucky':'western-kentucky-hilltoppers','Miami (FL)':'miami-hurricanes','Texas-El Paso':'utep-miners','Pittsburgh':'pittsburgh-panthers',
 'Southern Methodist':'smu-mustangs','Seattle':'seattle-u-redhawks','George Washington':'george-washington-revolutionaries','Virginia Commonwealth':'vcu-rams',
 'Pennsylvania':'pennsylvania-quakers','Texas Christian':'tcu-horned-frogs','Texas-Pan American':'ut-rio-grande-valley-vaqueros',
 'Nevada-Reno':'nevada-wolf-pack','Louisiana-Lafayette':'louisiana-ragin-cajuns','Alabama-Birmingham':'uab-blazers','Massachusetts':'massachusetts-minutemen',
 'Mississippi':'ole-miss-rebels','Long Island-Brooklyn':'long-island-university-sharks','North Carolina-Charlotte':'charlotte-49ers',
 'California-Santa Barbara':'uc-santa-barbara-gauchos',"St. Mary's (CA)":'saint-marys-gaels','Cal State-Fullerton':'cal-state-fullerton-titans',
 'New Orleans':'lsu-new-orleans-privateers','Middle Tennessee State':'middle-tennessee-blue-raiders','California-Irvine':'uc-irvine-anteaters',
 'Southern Mississippi':'southern-miss-golden-eagles','Louisiana-Monroe':'ul-monroe-warhawks','McNeese State':'mcneese-cowboys',
 'Loyola-Maryland':'loyola-maryland-greyhounds','Tennessee-Chattanooga':'chattanooga-mocs','Houston Baptist':'houston-christian-huskies',
 'Sam Houston State':'sam-houston-bearkats','California-Riverside':'uc-riverside-highlanders','North Carolina-Wilmington':'unc-wilmington-seahawks',
 'Wisconsin-Green Bay':'green-bay-phoenix','Appalachian State':'app-state-mountaineers','Texas-Arlington':'ut-arlington-mavericks',
 'Arkansas-Little Rock':'little-rock-trojans','Virginia Military Institute':'vmi-keydets','Texas A&M-Commerce':'east-texas-am-lions',
 'Maryland-Eastern Shore':'maryland-eastern-shore-hawks','Illinois-Chicago':'uic-flames','Texas-San Antonio':'utsa-roadrunners',
 'Fairleigh Dickinson':'fairleigh-dickinson-knights','Central Florida':'ucf-knights','Central Connecticut State':'central-connecticut-blue-devils',
 'Cal State-Northridge':'cal-state-northridge-matadors','Nebraska-Omaha':'omaha-mavericks','Nicholls State':'nicholls-colonels',
 'Wisconsin-Milwaukee':'milwaukee-panthers','Tennessee-Martin':'ut-martin-skyhawks','IUPUI':'iu-indianapolis-jaguars',
 'Cal State-Bakersfield':'cal-state-bakersfield-roadrunners','Missouri-Kansas City':'kansas-city-roos','California-San Diego':'uc-san-diego-tritons',
 'California-Davis':'uc-davis-aggies','Florida International':'florida-international-panthers','Maryland-Baltimore County':'umbc-retrievers',
 'Massachusetts Lowell':'umass-lowell-river-hawks','Southeastern Louisiana':'se-louisiana-lions','St. Thomas (MN)':'st-thomas-tommies'}
def build(doc):
 teams=[t for t in json.loads((ROOT/'data/sports/team-registry.json').read_text())['teams'] if t['sport']=='cbb'];names=defaultdict(set)
 for t in teams:
  for name in [t['short_name'],t['name'],*t.get('aliases',[])]:
   if name:names[norm(name)].add(t['slug'])
 for t in json.loads((ROOT/'data/cbb/tournament-team-map.json').read_text())['teams'].values():
  if t.get('slug'):names[norm(t['name'])].add(t['slug'])
 def resolve(org):
  if org in ALIASES:return ALIASES[org]
  hits=names.get(norm(org),set())
  if len(hits)==1:return next(iter(hits))
  hits={t['slug'] for t in teams if norm(t['name']).startswith(norm(org))}
  return next(iter(hits)) if len(hits)==1 else None
 rs=doc['resultSets'][0];rows=[dict(zip(rs['headers'],r)) for r in rs['rowSet']]
 years=Counter(int(r['SEASON']) for r in rows);assert min(years)==1947 and max(years)>=2026
 assert all(year in years for year in range(1947,2027))
 programs={t['slug']:[] for t in teams};unmapped=Counter();seen=set()
 for r in rows:
  if r['ORGANIZATION_TYPE']!='College/University':continue
  slug=resolve(r['ORGANIZATION'])
  if not slug:unmapped[r['ORGANIZATION']]+=1;continue
  assert slug in programs,slug
  key=(r['SEASON'],r['PERSON_ID'],r['TEAM_ID'],r['DRAFT_TYPE']);assert key not in seen;seen.add(key)
  programs[slug].append({'year':int(r['SEASON']),'player':r['PLAYER_NAME'],'round':r['ROUND_NUMBER'] or None,'pick':r['OVERALL_PICK'] or None,'draft_type':r['DRAFT_TYPE'],'nba_team':r['TEAM_CITY']+' '+r['TEAM_NAME'],'school':r['ORGANIZATION'],'source':'https://www.nba.com/stats/draft/history?Season='+r['SEASON']})
 for picks in programs.values():picks.sort(key=lambda p:(-p['year'],p['pick'] or 9999,p['player']))
 return {'source':'NBA Stats DraftHistory','source_url':SOURCE,'coverage':{'from':min(years),'through':max(years),'scope':'All draft rounds and territorial selections; NBA/BAA draft history, current program identities; NBA source organization determines school credit. Original selecting franchise, before rights trades. Unknown early round/pick numbers remain blank.'},'updated_at':datetime.now(timezone.utc).isoformat(),'programs':programs},unmapped
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--source-file',type=Path);args=ap.parse_args()
 if args.source_file:doc=json.loads(args.source_file.read_text())
 else:
  req=urllib.request.Request(SOURCE,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.nba.com/'})
  with urllib.request.urlopen(req,timeout=60) as r:doc=json.load(r)
 output,unmapped=build(doc)
 (ROOT/'data/cbb/nba-draft-history.json').write_text(json.dumps(output,separators=(',',':'),ensure_ascii=False)+'\n')
 print('Published',sum(map(len,output['programs'].values())),'selections for',sum(bool(x) for x in output['programs'].values()),'programs',output['coverage'])
 print('Unmatched source institutions (outside current registry or unresolved):',dict(unmapped))
