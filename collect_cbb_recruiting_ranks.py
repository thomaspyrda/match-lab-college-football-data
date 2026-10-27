"""Collect verified historical CBB recruiting rankings without inventing missing data.

Optional source: cbbstat.com team recruits feed (247Sports-derived), documented
in the toRvik R package. Failed requests do not overwrite existing verified data.
"""
import json, os, re, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/"data/cbb/recruiting-classes.json"
SOURCE="https://api.cbbstat.com/teams/recruits"
def clean(v):return re.sub(r"[^a-z0-9]+","-",str(v).lower()).strip("-")
def main():
    registry=json.loads((ROOT/"data/sports/team-registry.json").read_text())
    teams=[t for t in registry["teams"] if t["sport"]=="cbb"]
    choices={}
    for t in teams:
        slug=t["slug"]
        name=t.get("name") or t.get("display_name") or slug.replace("-"," ")
        choices.setdefault(clean(name),set()).add(slug)
        parts=slug.split("-")
        for length in range(1,min(5,len(parts))):
            choices.setdefault("-".join(parts[:length]),set()).add(slug)
    existing=json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {"source":SOURCE,"seasons":{}}
    total=0
    token=os.getenv("CBBD_API_KEY","").strip()
    for year in range(2016,2028):
        try:
            endpoint=("https://api.collegebasketballdata.com/recruiting/teams?year="+str(year)) if token else (SOURCE+"?year="+str(year))
            headers={"User-Agent":"BetWiseResearch/1.0"}
            if token:headers["Authorization"]="Bearer "+token
            req=urllib.request.Request(endpoint,headers=headers)
            with urllib.request.urlopen(req,timeout=15) as response:
                rows=json.load(response)
            if isinstance(rows,dict):rows=rows.get("data") or rows.get("results") or []
            if not isinstance(rows,list):raise ValueError("Expected ranking rows")
        except Exception as exc:
            print("Recruiting season",year,"source unavailable:",str(exc)[:140]);continue
        dest=existing["seasons"].setdefault(str(year),{})
        for item in rows:
            if not isinstance(item,dict):continue
            name=item.get("team") or item.get("school") or item.get("teamName")
            matches=choices.get(clean(name),set())
            rank=item.get("comp_rank") or item.get("rank") or item.get("nationalRank") or item.get("national_rank")
            if len(matches)!=1 or not rank:continue
            try:rank=int(rank)
            except(ValueError,TypeError):continue
            if not 1<=rank<=400:continue
            slug=next(iter(matches))
            if slug in dest:continue
            dest[slug]={"national_rank":rank,"points":item.get("comp_rating") or item.get("rating") or item.get("points"),"source":endpoint,"ranking_system":("CBBD composite" if token else "247Sports composite" if item.get("comp_rank") else "247Sports")}
            total+=1
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(existing,ensure_ascii=False,separators=(",",":"))+"\n")
    print("Added verified historical recruiting class ranks:",total)
if __name__=="__main__":main()
