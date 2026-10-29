"""Second official-archive pass: legacy StatCrew pages and schedule Stats links."""
import threading,re,html,argparse,shutil
from urllib.parse import urlsplit,urljoin
from pathlib import Path
import backfill_cbb_official_paint as base
from backfill_cbb_legacy_paint import classic,IDENTITIES

def main():
 p=argparse.ArgumentParser();p.add_argument('--merge',action='store_true');p.add_argument('--shard',type=int,default=0);p.add_argument('--shards',type=int,default=12);p.add_argument('--workers',type=int,default=5);p.add_argument('--cache-dir',default='/tmp/cbb-legacy-paint-cache');p.add_argument('--output',default='/tmp/official-paint-shard-0.json');p.add_argument('--input-dir',default='/tmp/official-paint-shards');args=p.parse_args()
 if args.merge:
  report=base.R/'data/cbb/official-paint-backfill-report.json'
  if report.exists():shutil.copyfile(report,base.R/'data/cbb/official-paint-first-pass-report.json')
  base.merge(args);return
 catalog=base.load(base.R/'data/cbb/official-paint-sources.json')['teams'];byhost={urlsplit(c['base_url']).netloc:(s,c) for s,c in catalog.items()};teams={t['slug']:t for t in IDENTITIES if t['sport']=='cbb'};context=threading.local();get=base.get;nuxt=base.parse_nuxt;links=base.links
 def tracked(url,cache,audit):
  context.owner=byhost.get(urlsplit(url).netloc)
  return get(url,cache,audit)
 def parse(body):
  record=nuxt(body)
  if record:return record
  owner=getattr(context,'owner',None)
  if not owner:return None
  slug,config=owner
  return classic(body,config['school_label'],teams[slug])
 def collect(body,root,year):
  urls=set(links(body,root,year))
  for attrs,text in re.findall(r'<a\b([^>]+)>(.*?)</a>',body,re.S):
   href=re.search(r'href=["\']([^"\']+)',attrs);label=html.unescape(re.sub('<[^>]+>',' ',text)).strip().lower()
   if not href or label not in ['stats','box score','boxscore']:continue
   url=urljoin(root,html.unescape(href[1]));parts=urlsplit(url)
   if parts.netloc!=urlsplit(root).netloc:continue
   if '/news/' in parts.path or '/boxscore.aspx' in parts.path.lower():urls.add(url.split('#')[0])
  return sorted(urls)
 base.get=tracked;base.parse_nuxt=parse;base.links=collect;base.crawl(args)
if __name__=='__main__':main()
