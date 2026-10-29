"""Second official-archive pass: legacy StatCrew pages and schedule Stats links."""
import threading,re,html,argparse,shutil,gzip,io,hashlib,urllib.request,urllib.error,tempfile,subprocess
from urllib.parse import urlsplit,urljoin
from pathlib import Path
import backfill_cbb_official_paint as base
from backfill_cbb_legacy_paint import classic,IDENTITIES

def main():
 p=argparse.ArgumentParser();p.add_argument('--custom-only',action='store_true');p.add_argument('--merge',action='store_true');p.add_argument('--shard',type=int,default=0);p.add_argument('--shards',type=int,default=12);p.add_argument('--workers',type=int,default=5);p.add_argument('--cache-dir',default='/tmp/cbb-legacy-paint-cache');p.add_argument('--output',default='/tmp/official-paint-shard-0.json');p.add_argument('--input-dir',default='/tmp/official-paint-shards');args=p.parse_args()
 if args.merge:
  report=base.R/'data/cbb/official-paint-backfill-report.json'
  if report.exists():shutil.copyfile(report,base.R/'data/cbb/official-paint-first-pass-report.json')
  base.merge(args);return
 catalog=base.load(base.R/'data/cbb/official-paint-sources.json')['teams'];byhost={urlsplit(c['base_url']).netloc:(s,c) for s,c in catalog.items()};teams={t['slug']:t for t in IDENTITIES if t['sport']=='cbb'};context=threading.local();get=base.get;nuxt=base.parse_nuxt;links=base.links
 def tracked(url,cache,audit):
  host=urlsplit(url).netloc
  if host in byhost:context.owner=byhost[host]
  # Public, verified historical schedule routes used by these official sites.
  wmt={'ramblinwreck.com':'m-baskbl','vucommodores.com':'mbball','virginiasports.com':'mbball'}
  season=re.search(r'/sports/mens-basketball/(?:stats|schedule)/(\d{4}-\d{2})$',urlsplit(url).path)
  if season and host in wmt:url='https://'+host+'/sports/'+wmt[host]+'/schedule/season/'+season[1]
  is_box=bool(re.search(r'/boxscore[/.]|/news/|\.pdf(?:[?#]|$)',url,re.I))
  if not is_box:context.failures=0
  if is_box and getattr(context,'failures',0)>=5:audit['archive_transport_circuit_break']+=1;return None
  target=cache/(hashlib.sha256(url.encode()).hexdigest()+'.html')
  if target.exists():return target.read_text()
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; BetWiseHistoricalResearch/1.0)','Accept-Encoding':'gzip'})
   with urllib.request.urlopen(req,timeout=16) as response:
    body=response.read(7_000_000);encoding=response.headers.get('Content-Encoding','')
   if encoding=='gzip':body=gzip.GzipFile(fileobj=io.BytesIO(body)).read(20_000_000)
   if body.startswith(b'%PDF-'):
    result=subprocess.run(['pdftotext','-layout','-','-'],input=body,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
    if result.returncode:audit['unreadable_pdf']+=1;return None
    text='<pre>'+html.escape(result.stdout.decode('utf-8','replace'))+'</pre>';audit['official_pdfs_read']+=1
   else:text=body.decode('utf-8','replace')
   target.write_text(text);context.failures=0;return text
  except urllib.error.HTTPError as e:audit['http_'+str(e.code)]+=1
  except Exception as e:audit['request_'+type(e).__name__]+=1
  if is_box:context.failures=getattr(context,'failures',0)+1
  return None
 def parse(body):
  record=nuxt(body)
  if record:return record
  owner=getattr(context,'owner',None)
  if not owner:return None
  slug,config=owner
  return classic(body,config['school_label'],teams[slug])
 def collect(body,root,year):
  urls=set() if args.custom_only else set(links(body,root,year))
  for attrs,text in re.findall(r'<a\b([^>]+)>(.*?)</a>',body,re.S):
   href=re.search(r'href=["\']([^"\']+)',attrs);label=html.unescape(re.sub('<[^>]+>',' ',text)).strip().lower()
   if not href or not any(x in label for x in ['stats','box score','boxscore']):continue
   url=urljoin(root,html.unescape(href[1]));parts=urlsplit(url)
   is_pdf=parts.path.lower().endswith('.pdf')
   custom=bool(re.search(r'\.html?$|/custompages/|/Stats_',parts.path,re.I)) and 'boxscore' not in parts.path.lower()
   if args.custom_only and not custom:continue
   if parts.netloc!=urlsplit(root).netloc:
    trusted=parts.netloc.endswith('.amazonaws.com') or parts.netloc=='storage.googleapis.com' or parts.netloc.startswith('static.') or parts.netloc.endswith('.sidearmsports.com')
    if not trusted or not (is_pdf or custom):continue
   if custom or is_pdf or '/news/' in parts.path or 'boxscore' in parts.path.lower():urls.add(url.split('#')[0])
  return sorted(urls)
 base.get=tracked;base.parse_nuxt=parse;base.links=collect;base.crawl(args)
if __name__=='__main__':main()
