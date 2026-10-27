"""Normalize previously imported CBB tournament labels without changing outcomes."""
import csv,io,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=ROOT/"data/cbb/conference-tournament-results.json"
d=json.loads(p.read_text())
registry=json.loads((ROOT/"data/sports/team-registry.json").read_text())
teams=[x for x in registry["teams"] if x["sport"]=="cbb"]
names={t["slug"]:t.get("short_name") or t["name"] for t in teams}
ids={}
try:
    url="https://huggingface.co/Jensen-holm/Nigl/resolve/main/data/MTeams.csv"
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=20) as r:
        for row in csv.DictReader(io.StringIO(r.read().decode("utf-8-sig"))):
            ids[row["TeamID"]]=row["TeamName"]
except Exception as error:
    print("Team-ID lookup unavailable; keeping unresolved IDs:",error)
confs={"a_sun":"ASUN","a_ten":"Atlantic 10","acc":"ACC","aac":"AAC","sec":"SEC","big_ten":"Big Ten","big_twelve":"Big 12","big_east":"Big East","big_sky":"Big Sky","big_south":"Big South","big_west":"Big West","cusa":"Conference USA","ivy":"Ivy League","mac":"MAC","maac":"MAAC","mvc":"Missouri Valley","mwc":"Mountain West","pac_twelve":"Pac-12","patriot":"Patriot League","socon":"Southern","sun_belt":"Sun Belt","wcc":"WCC","wac":"WAC","swac":"SWAC","meac":"MEAC","horizon":"Horizon League","summit":"Summit League"}
def nice(x):
    if x in names:return names[x]
    if x in ids:return ids[x]
    if x in confs:return confs[x]
    return x
changed=0
for year,season in d["seasons"].items():
    for slug,entry in season.items():
        value=entry.get("result")
        if not value:continue
        fresh=value
        for key in sorted(set(re.findall(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)+|\b\d{4}\b|[a-z]+_[a-z_]+",value)),key=len,reverse):
            if key in names or key in ids or key in confs:
                fresh=fresh.replace(key,nice(key))
        fresh=re.sub(r"\b([a-z][a-z0-9_]+) Tournament",lambda m:confs.get(m.group(1),m.group(1).upper())+" Tournament",fresh)
        if fresh!=value:
            entry["result"]=fresh
            changed+=1
p.write_text(json.dumps(d,ensure_ascii=False,separators=(",",":"))+"\n")
print("Normalized conference results:",changed)
