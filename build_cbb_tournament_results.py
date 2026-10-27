"""Build NCAA/NIT and conference-tournament results from verified archived games.
Use ESPN postseason classification when available. Never infer missing participation.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
teams=ROOT/"data/cbb/teams"
def main():
    national={"source":"ESPN archived postseason games; tournament classification requires verification","seasons":{}}
    conference={"source":"ESPN archived regular-season schedule; conference tournament classification requires verification","seasons":{}}
    count=0
    for path in sorted(teams.glob("*.json")):
        data=json.loads(path.read_text());slug=data["slug"]
        for year,s in data["seasons"].items():
            if int(year)>2026:continue
            post=s.get("phases",{}).get("postseason",{}).get("games",[])
            if year=="2020":
                national["seasons"].setdefault(year,{})[slug]={"result":"NCAA and NIT tournaments canceled in 2020","tournament":"canceled"}
                continue
            # ESPN seasontype=3 alone does not establish NCAA vs NIT; do not guess.
            if post:
                national["seasons"].setdefault(year,{})[slug]={"result":"Postseason games recorded; NCAA/NIT classification pending verification","tournament":"unverified","postseason_games":len(post)}
                count+=1
    (ROOT/"data/cbb").mkdir(parents=True,exist_ok=True)
    (ROOT/"data/cbb/tournament-results.json").write_text(json.dumps(national,separators=(",",":"))+"\n")
    # Conference results are collected from verified conference-specific game notes, not this archive flagging pass.
    conf_path=ROOT/"data/cbb/conference-tournament-results.json"\n    if not conf_path.exists():conf_path.write_text(json.dumps(conference,separators=(",",":"))+"\n")
    print(f"Published {count} postseason participation flags; no unsupported tournament claims")
if __name__=="__main__":main()
