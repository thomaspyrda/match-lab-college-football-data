#!/usr/bin/env python3
"""Conservative TeamRankings MLB matchup-page collector.

Reads publicly accessible HTML pages, respects robots.txt, identifies favorited
teams from the published 'Odds: NAME by 1.5' header, and records source URLs.
No login, proxy rotation, CAPTCHA bypass, or bulk re-hosting.
"""
import argparse
import html
import json
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser

USER_AGENT="BetWiseHistoricalResearch/1.0 (historical MLB line attribution)"
ROOT=pathlib.Path(__file__).resolve().parents[1]

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.words=[]
        self.links=[]
        self.href=None
    def handle_starttag(self,tag,attrs):
        if tag=="a":self.href=dict(attrs).get("href")
    def handle_data(self,data):
        if data.strip():
            self.words.append(data.strip())
            if self.href:self.links.append((data.strip(),self.href))
    def handle_endtag(self,tag):
        if tag=="a":self.href=None

def parse_page(source,url):
    p=Page();p.feed(source)
    text=" ".join(p.words)
    odds=re.search(r"Odds:\s*([^|]{2,80}?)\s+by\s+(1\.5)\b",text,re.I)
    date=re.search(r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b",text,re.I)
    return {"url":url,"favorite_label":odds.group(1).strip() if odds else None,
            "runline":float(odds.group(2)) if odds else None,
            "matchup_date_text":date.group(0) if date else None,
            "links":[urllib.parse.urljoin(url,h) for _,h in p.links if "/mlb/matchup/" in h]}

def collect(urls,delay,limit):
    robots=urllib.robotparser.RobotFileParser()
    robots.set_url("https://www.teamrankings.com/robots.txt")
    try:robots.read()
    except Exception as ex:
        raise SystemExit("Robots policy inaccessible; skipping collection: "+str(ex))
    results=[]
    for url in urls[:limit]:
        parsed=urllib.parse.urlsplit(url)
        if parsed.hostname not in ("www.teamrankings.com","www2.teamrankings.com","teamrankings.com"):
            continue
        if not robots.can_fetch(USER_AGENT,url):
            print("SKIP robots disallow:",url,flush=True);continue
        try:
            req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"text/html"})
            with urllib.request.urlopen(req,timeout=20) as resp:
                if resp.status!=200 or "html" not in resp.headers.get("Content-Type",""):
                    continue
                source=resp.read(1024*1024).decode("utf-8","replace")
            item=parse_page(source,url)
            if item["favorite_label"] and item["runline"]==1.5:
                results.append(item)
            else:print("SKIP no unambiguous favorite:",url,flush=True)
        except (urllib.error.URLError,TimeoutError) as ex:
            print("FETCH FAILED:",url,str(ex),flush=True)
        time.sleep(max(2,delay))
    return results

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--urls",type=pathlib.Path,required=True,help="newline-separated historical TeamRankings matchup URLs")
    p.add_argument("--output",type=pathlib.Path,default=pathlib.Path("teamrankings-pilot.json"))
    p.add_argument("--delay",type=float,default=4)
    p.add_argument("--limit",type=int,default=10)
    a=p.parse_args()
    urls=[line.strip() for line in a.urls.read_text().splitlines() if line.strip() and not line.startswith("#")]
    result=collect(urls,a.delay,min(max(a.limit,1),100))
    a.output.write_text(json.dumps({"source":"TeamRankings matchup page","matches":result},indent=2)+"\n")
    print(json.dumps({"requested":min(len(urls),a.limit),"parsed":len(result),"output":str(a.output)}))
if __name__=="__main__":main()
