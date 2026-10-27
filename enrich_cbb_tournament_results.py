"""Enrich archived NCAA and NIT tournament results from ESPN group-specific scoreboards.
Fail closed: never replace verified historical seasons with empty/incomplete feeds.
"""
import json, re, urllib.request, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"data/cbb/tournament-results.json"
BASE="https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
def fetch(year,group):
    url=f"{BASE}?dates={year}0310-{year}0415&groups={group}&limit=1200"
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"BetWiseResearch/1.0"}),timeout=35) as rsp:
        data=json.load(rsp)
    return data.get("events",[])
def events_for_team(items,id_slug):
    out={}
    for ev in items:
        if not ev.get("status",{}).get("type",{}).get("completed",False):continue
        for comp in (ev.get("competitions") or [])[:1]:
            notes=" ".join(str(x.get("headline","")) for x in comp.get("notes",[]))
            notes+=" "+str(ev.get("name",""))+" "+str(ev.get("shortName",""))
            for team in comp.get("competitors",[]):
                slug=id_slug.get(str(team.get("team",{}).get("id","")))
                if not slug:continue
                out.setdefault(slug,[]).append({"date":ev.get("date",""),"win":team.get("winner") is True,"notes":notes,"event":str(ev.get("id",""))})
    return out
def ncaa_result(games):
    games=sorted(games,key=lambda g:g["date"])
    count=len(games)
    wins=sum(g["win"] for g in games)
    last=games[-1]
    note=last["notes"].lower()
    if wins>=6 and all(x["win"] for x in games):return "NCAA Tournament · National Champion"
    if count>=6:return "NCAA Tournament · National Runner-up"
    if count==5:return "NCAA Tournament · Final Four"
    if count==4:return "NCAA Tournament · Elite Eight"
    if count==3:return "NCAA Tournament · Sweet 16"
    if count==2:return "NCAA Tournament · Round of 32"
    if "first four" in note:return "NCAA Tournament · First Four"
    return "NCAA Tournament · Round of 64"
def main():
    db=json.loads(OUT.read_text())
    reg=json.loads((ROOT/"data/sports/team-registry.json").read_text())
    id_slug={str(t["espn_id"]):t["slug"] for t in reg["teams"] if t["sport"]=="cbb"}
    for year in range(2016,2027):
        if year==2020:continue
        try:
            ncaa=fetch(year,100)
            if len(ncaa)<40:raise ValueError(f"Only {len(ncaa)} NCAA games")
            time.sleep(.3)
            wide=fetch(year,50)
            if len(wide)<100:raise ValueError(f"Only {len(wide)} wider March games")
        except Exception as e:
            print(year,"incomplete source:",str(e)[:130]);continue
        n=events_for_team(ncaa,id_slug)
        ncaa_ids={str(x.get("id")) for x in ncaa}
        nit_items=[]
        for ev in wide:
            if str(ev.get("id")) in ncaa_ids:continue
            comp=(ev.get("competitions") or [{}])[0]
            notes=" ".join(str(x.get("headline","")) for x in comp.get("notes",[]))
            title=ev.get("name","")+" "+ev.get("shortName","")+" "+notes
            if re.search(r"\bNIT\b|National Invitation Tournament",title,re.I):
                nit_items.append(ev)
        nit=events_for_team(nit_items,id_slug)
        results=db["seasons"].setdefault(str(year),{})
        for slug,games in n.items():
            results[slug]={"tournament":"NCAA","result":ncaa_result(games),"games":len(games),"source":"ESPN NCAA Tournament scoreboard (group 100)"}
        for slug,games in nit.items():
            if slug in n:continue
            games=sorted(games,key=lambda x:x["date"])
            count=len(games)
            if count>=5 and games[-1]["win"]:label="NIT Tournament · Champion"
            elif count>=5:label="NIT Tournament · Runner-up"
            elif count>=4:label="NIT Tournament · Semifinalist"
            elif count==3:label="NIT Tournament · Quarterfinalist"
            elif count==2:label="NIT Tournament · Second Round"
            else:label="NIT Tournament · First Round"
            results[slug]={"tournament":"NIT","result":label,"games":count,"source":"ESPN scoreboard NIT competition notes"}
        print(year,"verified NCAA:",len(n),"NIT:",len(nit))
    OUT.write_text(json.dumps(db,separators=(",",":"),ensure_ascii=False)+"\n")
if __name__=="__main__":main()
