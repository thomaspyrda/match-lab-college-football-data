#!/usr/bin/env python3
"""Audit Bart Torvik's original 2016–2020 preseason projection pages.

No fallback to in-season or final ratings. Save source HTML and a candidate CSV
for a human-reviewable import, never publish without checking source usage rights.
"""
import argparse,csv,re,json,sys
from pathlib import Path
from urllib.request import Request,urlopen
from bs4 import BeautifulSoup

def parse(html):
    soup=BeautifulSoup(html,"html.parser")
    candidates=[]
    for table in soup.find_all("table"):
        entries=[]
        for row in table.find_all("tr"):
            cells=row.find_all(["td"],recursive=False)
            if len(cells)<3:continue
            first=cells[0].get_text(" ",strip=True)
            if not re.fullmatch(r"#?\s*\d{1,3}\.?",first):continue
            rank=int(re.search(r"\d+",first).group())
            if not 1<=rank<=400:continue
            # Team typically occupies the second or third column of T-Rank tables.
            next_cells=[c.get_text(" ",strip=True) for c in cells[1:4]]
            team=next((x for x in next_cells if re.search(r"[A-Za-z]{3}",x) and not re.fullmatch(r"(?:\d+[.\d%\-]*)",x)),None)
            if team:
                entries.append((rank,team))
        if len(entries)>len(candidates):candidates=entries
    return candidates

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--start",type=int,default=2016)
    ap.add_argument("--end",type=int,default=2020)
    ap.add_argument("--directory",type=Path,default=Path("cbb/match-lab/imports/preseason-review"))
    ap.add_argument("--minimum",type=int,default=300)
    args=ap.parse_args()
    args.directory.mkdir(parents=True,exist_ok=True)
    summary={}
    for year in range(args.start,args.end+1):
        url=f"https://barttorvik.com/trankpure{year%100:02d}.php"
        try:
            response=urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; historical CBB research)"}),timeout=30)
            html=response.read().decode("utf-8",errors="replace")
        except Exception as e:
            print(f"{year}: source inaccessible: {type(e).__name__}: {e}",file=sys.stderr)
            summary[str(year)]={"source":url,"retrieved":False,"count":0}
            continue
        (args.directory/f"{year}-source.html").write_text(html)
        entries=parse(html)
        uniques={r:t for r,t in entries}
        complete=len(uniques)>=args.minimum and len(set(uniques.values()))==len(uniques)
        with (args.directory/f"{year}-candidates.csv").open("w",newline="") as stream:
            writer=csv.writer(stream)
            writer.writerow(["season","team","rank","source_url"])
            for rank,team in sorted(uniques.items()):
                writer.writerow([year,team,rank,url])
        summary[str(year)]={"source":url,"retrieved":True,"candidates":len(uniques),"complete":complete}
        print(f"{year}: {len(uniques)} candidate ranks, complete={complete}")
    (args.directory/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    if not all(x.get("complete") for x in summary.values()):
        raise SystemExit("Incomplete or inaccessible preseason archive. Candidate data NOT published.")
if __name__=="__main__":main()
