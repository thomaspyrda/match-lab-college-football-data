"""Recover official legacy StatCrew boxes linked as Stats on men's schedules."""
import re,json,html,argparse,urllib.parse
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
from backfill_cbb_official_paint import R,load,save,get

def norm(v):return re.sub('[^a-z0-9]','',str(v).lower())
IDENTITIES=load(R/'data/sports/team-registry.json')['teams']
def classic(s,school,team):
 pres=re.findall(r'<pre\b[^>]*>(.*?)</pre>',s,re.S)
 alltext='\n'.join(html.unescape(re.sub('<[^>]+>',' ',raw)) for raw in pres)
 summary=re.search(r'POINTS IN PAINT[^\n]*\n(.*?)(?:\n\s*\n|$)',alltext,re.S|re.I)
 summarypaint={norm(n):int(v) for n,v in re.findall(r'^\s*(.*?)\.{2,}\s+[\d\s]+-\s*(\d+)\s*$',summary[1],re.M)} if summary else {}
 for raw in pres:
  text=html.unescape(re.sub('<[^>]+>',' ',raw));text=text.replace('\r','')
  if 'Official Basketball Box Score' not in text:continue
  date=re.search(r'\b\d{1,2}[/-]\d{1,2}[/-](?:\d{4}|\d{2})\b',text);vis=re.search(r'^\s*VISITORS:\s*(.*?)\s+\(?\d+\s*-\s*\d+',text,re.M);home=re.search(r'^\s*HOME TEAM:\s*(.*?)\s+\(?\d+\s*-\s*\d+',text,re.M)
  paint=re.search(r'Points in the paint-([^,\s]+)\s+(\d+)\s*,\s*([^.,\s]+)\s+(\d+)\s*\.',text,re.I)
  if not all([date,vis,home]) or not paint and not summarypaint:continue
  scores=re.findall(r'^\s*(.*?)\.{2,}\s+[\d\s]+-\s*(\d+)\s*$',text.split('Score by Periods',1)[-1],re.M)
  score={norm(n):int(v) for n,v in scores};names=[vis[1].strip(),home[1].strip()]
  if any(norm(n) not in score for n in names):continue
  codes=[paint[1],paint[3]] if paint else [];vals=[int(paint[2]),int(paint[4])] if paint else []
  def code_matches(code,name):
   c=norm(code);v=norm(name);initials=norm(''.join(w[0] for w in re.findall('[A-Za-z]+',name)))
   known=set()
   for t in IDENTITIES:
    aliases=[t.get('name',''),t.get('short_name',''),*t.get('aliases',[])]
    if v in {norm(x) for x in aliases}:
     known.update(norm(x) for x in aliases)
   known.update({'uk':'kentucky','iu':'indiana','uwm':'milwaukee'}.keys() if v in ['kentucky','indiana','milwaukee'] and {'uk':'kentucky','iu':'indiana','uwm':'milwaukee'}.get(c)==v else [])
   return c==v or len(c)>=2 and v.startswith(c) or c==initials or c in known
  mapping=[]
  for c in codes:
   matches=[i for i,n in enumerate(names) if code_matches(c,n)]
   mapping.append(matches[0] if len(matches)==1 else None)
  if len(mapping)==2 and mapping.count(None)==1:
   used=next(x for x in mapping if x is not None);mapping[mapping.index(None)]=1-used
  has_summary=all(norm(n) in summarypaint for n in names)
  if not has_summary and sorted(x for x in mapping if x is not None)!=[0,1]:continue
  aliases={norm(x) for x in [school,team['name'],team['short_name'],*team.get('aliases',[])] if x};own=[i for i,n in enumerate(names) if norm(n) in aliases or len(norm(n))>=4 and norm(team['name']).startswith(norm(n))]
  if len(own)!=1:continue
  i=own[0];pv={j:summarypaint[norm(names[j])] for j in range(2)} if has_summary else {mapping[j]:vals[j] for j in range(2)};a,b=pv[i],pv[1-i];p,q=score[norm(names[i])],score[norm(names[1-i])]
  if a<0 or b<0 or a>p or b>q or a%2 or b%2 or a+b==0:continue
  stamp=None
  for fmt in ['%m/%d/%y','%m/%d/%Y','%m-%d-%y','%m-%d-%Y']:
   try:stamp=datetime.strptime(date[0],fmt).date().isoformat();break
   except ValueError:pass
  if not stamp:continue
  return {'date':stamp,'points':p,'opponent_points':q,'paint_for':a,'paint_against':b,'format':'Official whole-game StatCrew box; matched final score'}
 return None

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--team',default='duke-blue-devils');ap.add_argument('--year',type=int,default=2016);ap.add_argument('--output',default='/tmp/official-legacy-observations.json');args=ap.parse_args();catalog=load(R/'data/cbb/official-paint-sources.json')['teams'];config=catalog[args.team];registry=load(R/'data/sports/team-registry.json')['teams'];byid={str(t['espn_id']):t['slug'] for t in registry if t['sport']=='cbb'};team=next(t for t in registry if t['slug']==args.team);year=str(args.year);base=config['base_url'];a=load(R/f'data/cbb/teams/{args.team}.json');games={}
 for phase in a['seasons'][year]['phases'].values():
  for g in phase.get('games',[]):
   if g.get('status')=='final':
    day=datetime.fromisoformat(g['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date().isoformat();games[(day,g['points'],g['opponent_points'])]=g
 audit=Counter();cache=Path('/tmp/cbb-legacy-paint-cache');cache.mkdir(exist_ok=True);label=f'{args.year-1}-{str(args.year)[-2:]}';url=base+'/sports/mens-basketball/schedule/'+label;body=get(url,cache,audit)
 if not body:raise RuntimeError('Official schedule unavailable')
 urls=set()
 for attrs,inner in re.findall(r'<a\b([^>]+)>(.*?)</a>',body,re.S):
  m=re.search(r'href=["\']([^"\']+)',attrs);text=html.unescape(re.sub('<[^>]+>',' ',inner)).strip().lower()
  if m and text in ['stats','box score','boxscore']:
   link=urllib.parse.urljoin(base,html.unescape(m[1]));p=urllib.parse.urlsplit(link)
   if p.netloc==urllib.parse.urlsplit(base).netloc and '/news/' in p.path:urls.add(link)
 def extract(link):
  b=get(link,cache,audit)
  if not b:return []
  box=classic(b,config['school_label'],team)
  if not box:return []
  g=games.get((box['date'],box['points'],box['opponent_points']))
  if not g:return []
  opponent=byid.get(str(g.get('opponent_id')));record={**box,'year':year,'game_id':g['id'],'team':args.team,'opponent':opponent,'source':link};out=[record]
  if opponent:out.append({**record,'team':opponent,'opponent':args.team,'points':box['opponent_points'],'opponent_points':box['points'],'paint_for':box['paint_against'],'paint_against':box['paint_for']})
  return out
 records=[]
 with ThreadPoolExecutor(3) as ex:
  for out in ex.map(extract,sorted(urls)):records+=out
 save(Path(args.output),{'records':records,'audit':dict(audit),'links':sorted(urls)});print('Official legacy links',len(urls),'verified observations',len(records),'games',len({r['game_id'] for r in records}),flush=True)
if __name__=='__main__':main()
