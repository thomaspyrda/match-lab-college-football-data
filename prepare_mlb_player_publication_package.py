#!/usr/bin/env python3
"""Prepare 30 MLB player-stat pages and one data asset in an isolated review directory.
No production writes. Intended for a separately reviewed publication commit.
"""
import argparse, json, re, shutil, hashlib
from pathlib import Path
from html import unescape

ROOT=Path(__file__).resolve().parent
BASE='/sports-research/mlb-historical-player-leaders.js'
SCRIPT='<script defer src="'+BASE+'?v=1" data-mlb-player-stats="2015-2026"></script>'
def prepare(archive,crosswalk,out):
    if archive.get("published") is not False or archive.get("status")!="MLB_HISTORICAL_LEADERS_REVIEW_ONLY":
        raise ValueError("Unpublished reviewed dataset required")
    mapped=crosswalk["teams"]
    if len(mapped)!=30 or len(archive["teams"])!=30: raise ValueError("Require 30 mapped and archived teams")
    dest=Path(out)
    if dest.resolve()==ROOT.resolve() or ROOT.resolve() in dest.resolve().parents:
        raise ValueError("Destination must be outside repository source tree")
    entries={}
    seen=set()
    for tid,seasons in archive["teams"].items():
        if tid not in mapped:raise ValueError("Unmapped MLB ID "+tid)
        slug=mapped[tid]["slug"]
        if slug in seen:raise ValueError("Duplicate slug "+slug)
        seen.add(slug)
        years={}
        for year in map(str,range(2015,2027)):
            group=seasons.get(year)
            if not group:raise ValueError(f"Missing {slug}/{year}")
            h=[r for r in group["hitters"] if int(r["stats"]["atBats"])>0]
            def pack(row,fields):
                return {"id":row["player_id"],"name":row["name"],
                        **{key:row["stats"].get(field) for key,field in fields.items()}}
            hitters=[pack(r,{"ab":"atBats","h":"hits","r":"runs","hr":"homeRuns","rbi":"rbi","avg":"avg","obp":"obp","ops":"ops"}) for r in h]
            pitching={"gp":"gamesPlayed","gs":"gamesStarted","ip":"inningsPitched","era":"era","whip":"whip","so":"strikeOuts","w":"wins","l":"losses","sv":"saves"}
            starters=[pack(r,pitching) for r in group["starters"]]
            relievers=[pack(r,pitching) for r in group["relievers"]]
            if len(hitters)>20 or len(starters)!=5 or len(relievers)!=5:raise ValueError(f"Invalid {slug}/{year} counts")
            if any(hitters[i]["ab"]<hitters[i+1]["ab"] for i in range(len(hitters)-1)):raise ValueError("Bad AB ordering")
            if set(x["id"] for x in starters)&set(x["id"] for x in relievers):raise ValueError("Duplicate pitcher")
            years[year]={"hitters":hitters,"starters":starters,"relievers":relievers}
        entries[slug]=years
        src=ROOT/"mlb"/"teams"/slug/"index.html"
        if not src.exists():raise ValueError("Missing team page "+slug)
        html=src.read_text()
        if html.count('id="team-season-data"')!=1:raise ValueError("Unexpected team data "+slug)
        existing=re.findall(r'<script[^>]*data-mlb-player-stats[^>]*></script>',html)
        if len(existing)>1:raise ValueError("Multiple player scripts "+slug)
        if existing:
            html=html.replace(existing[0],SCRIPT,1)
        else:
            if html.count("</body>")!=1:raise ValueError("Missing or multiple body closing tags "+slug)
            html=html.replace("</body>",SCRIPT+"</body>",1)
        page=dest/"mlb"/"teams"/slug/"index.html"
        page.parent.mkdir(parents=True,exist_ok=True)
        page.write_text(html)
    if len(entries)!=30:raise ValueError("Missing team")
    # Team-scoped payloads avoid transferring every franchise's entire archive on each page.
    for slug,years in entries.items():
        target=dest/"data"/"mlb"/"historical-players"/(slug+".json")
        target.parent.mkdir(parents=True,exist_ok=True)
        data={"status":"MLB_HISTORICAL_PLAYER_LEADERS","slug":slug,
              "seasons":[2015,2026],"published":False,
              "source":"MLB Stats API team-specific regular-season splits","years":years}
        target.write_text(json.dumps(data,separators=(",",":"),ensure_ascii=False)+"\n")
    js=ROOT/"sports-research"/"mlb-historical-player-leaders.js"
    if not js.exists():raise ValueError("Missing player renderer JS")
    rendered=dest/"sports-research"/js.name
    rendered.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(js,rendered)
    paths=list(dest.rglob("*"))
    manifest={"status":"REVIEW_ONLY_NOT_PUBLISHED","teams":len(entries),
              "seasons_per_team":12,"files":[{"path":p.relative_to(dest).as_posix(),
              "sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths if p.is_file()]}
    (dest/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"status":manifest["status"],"teams":len(entries),"files":len(manifest["files"]),"publication":False}))
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--input",required=True)
    a.add_argument("--crosswalk",required=True)
    a.add_argument("--out",required=True)
    opts=a.parse_args()
    prepare(json.loads(Path(opts.input).read_text()),json.loads(Path(opts.crosswalk).read_text()),opts.out)
if __name__=="__main__":main()
