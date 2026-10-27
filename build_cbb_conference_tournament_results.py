"""Collect sourced conference tournament results from ESPN scoreboard event notes.
No guessed conference titles, rounds, or missing tournament participation.
"""
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"data/cbb/conference-tournament-results.json"
BASE="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
def fetch(year):
    url=f"{BASE}?dates={year}0301-{year}0320&limit=1500"
    req=urllib.request.Request(url,headers={"User-Agent":"BetWiseResearch/1.0"})
    with urllib.request.urlopen(req,timeout=35) as response:return json.load(response)
def main():
    ids={str(t["espn_id"]):t["slug"] for t in json.loads((ROOT/"data/sports/team-registry.json").read_text())["teams"] if t["sport"]=="cbb"}
    db=json.loads(OUT.read_text()) if OUT.exists() else {"source":"ESPN men's basketball scoreboard, conference tournament notes","seasons":{}}
    for year in range(2016,2027):
        if year==2020:
            previous=db["seasons"].get("2020",{})
            db["seasons"]["2020"]={slug:{**previous.get(slug,{}),"result":"Conference tournaments canceled or interrupted in 2020","status":"canceled"} for slug in ids.values()}
            continue
        try:
            events=fetch(year).get("events",[])
            if len(events)<100:raise ValueError("Insufficient scoreboard events")
        except Exception as e:
            print(f"{year}: source unavailable or incomplete ({str(e)[:100]})");continue
        matched={}
        for event in events:
            for comp in event.get("competitions",[])[:1]:
                notes=" ".join(str(n.get("headline","")) for n in comp.get("notes",[]))
                label=(event.get("name","")+" "+event.get("shortName","")+" "+notes).lower()
                if not re.search(r"conference tournament|\b(?:acc|sec|big ten|big 12|big east|pac-12|wcc|aac|a-10) tournament\b",label):continue
                if "ncaa" in label or "national invitation" in label or "nit tournament" in label:continue
                finished=event.get("status",{}).get("type",{}).get("completed",False)
                if not finished:continue
                for competitor in comp.get("competitors",[]):
                    tid=str(competitor.get("team",{}).get("id",""))
                    if tid not in ids:continue
                    matched.setdefault(ids[tid],[]).append({"date":event.get("date",""),"win":bool(competitor.get("winner")),"title":notes})
        season={}
        for slug,games in matched.items():
            games.sort(key=lambda x:x["date"])
            last=games[-1]
            if last["win"] and re.search(r"championship|final",last["title"],re.I):
                label="Conference Tournament Champion"
            elif not last["win"]:
                label="Conference Tournament · Eliminated"
            else:
                label="Conference Tournament · Participated"
            season[slug]={"result":label,"games":len(games),"source":"ESPN scoreboard competition notes"}
        if season:
            previous=db["seasons"].setdefault(str(year),{})
            for slug,fields in season.items():
                previous.setdefault(slug,{}).update(fields)
        print(year,len(season),"verified conference tournament participants")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(db,separators=(",",":"),ensure_ascii=False)+"\n")
if __name__=="__main__":main()
