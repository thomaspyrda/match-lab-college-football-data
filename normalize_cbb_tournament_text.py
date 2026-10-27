"""Normalize previously imported CBB tournament labels without changing outcomes."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
registry=json.loads((ROOT/"data/sports/team-registry.json").read_text())
teams=[x for x in registry["teams"] if x["sport"]=="cbb"]
names={t["slug"]:t.get("short_name") or t["name"] for t in teams}
ids={key:value["name"] for key,value in json.loads((ROOT/"data/cbb/tournament-team-map.json").read_text())["teams"].items()}
confs={"a_east":"America East","aec":"America East","nec":"NEC","southland":"Southland","ovc":"OVC","a_sun":"ASUN","a_ten":"Atlantic 10","acc":"ACC","aac":"AAC","sec":"SEC","big_ten":"Big Ten","big_twelve":"Big 12","big_east":"Big East","big_sky":"Big Sky","big_south":"Big South","big_west":"Big West","cusa":"Conference USA","ivy":"Ivy League","mac":"MAC","maac":"MAAC","mvc":"Missouri Valley","mwc":"Mountain West","pac_twelve":"Pac-12","patriot":"Patriot League","socon":"Southern","sun_belt":"Sun Belt","wcc":"WCC","wac":"WAC","swac":"SWAC","meac":"MEAC","horizon":"Horizon League","summit":"Summit League"}
def nice(x):
    if x in names:return names[x]
    if x in ids:return ids[x]
    if x in confs:return confs[x]
    return x
def normalize_file(path):
    d=json.loads(path.read_text())
    changed=0
    for season in d["seasons"].values():
        for entry in season.values():
            value=entry.get("result")
            if not value:continue
            fresh=value
            for team in sorted(teams,key=lambda t:len(t["name"]),reverse=True):
                fresh=re.sub(r"(?<![\w-])"+re.escape(team["name"])+r"(?![\w-])",lambda _:team.get("short_name") or team["name"],fresh)
            for key in sorted(set(re.findall(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)+|\b\d{4}\b|[a-z]+_[a-z_]+",value)),key=len,reverse=True):
                if key in names or key in ids or key in confs:
                    fresh=re.sub(r"(?<![\w-])"+re.escape(key)+r"(?![\w-])",lambda _:nice(key),fresh)
            fresh=re.sub(r"\b([a-z][a-z0-9_]+) Tournament",lambda m:confs.get(m.group(1),m.group(1).upper())+" Tournament",fresh)
            if fresh!=value:
                entry["result"]=fresh
                changed+=1
    path.write_text(json.dumps(d,ensure_ascii=False,separators=(",",":"))+"\n")
    print(path.name,"normalized labels:",changed)
if __name__=="__main__":
    for filename in ("conference-tournament-results.json","tournament-results.json"):
        normalize_file(ROOT/"data/cbb"/filename)
