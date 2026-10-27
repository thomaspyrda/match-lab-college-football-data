"""Enrich sourced NCAA finishes with actual last-game scores from frozen CBB archives."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent
path=root/"data/cbb/tournament-results.json"
db=json.loads(path.read_text())
updated=0
for teamfile in (root/"data/cbb/teams").glob("*.json"):
    team=json.loads(teamfile.read_text())
    slug=team["slug"]
    for year,season in team["seasons"].items():
        item=db.get("seasons",{}).get(year,{}).get(slug)
        if not item or item.get("tournament")!="NCAA" or not isinstance(item.get("seed"),int):continue
        if item.get("eliminated_by"):continue
        games=[g for g in season.get("phases",{}).get("postseason",{}).get("games",[]) if g.get("status")=="final"]
        losses=[g for g in games if g.get("result")=="L"]
        if not losses:
            continue
        last=losses[-1]
        if last.get("points") is None or last.get("opponent_points") is None:continue
        result=item.get("result","")
        if "Eliminated in" not in result:continue
        school=last.get("opponent_name") or last.get("opponent")
        if not school:continue
        score=f'{last["points"]}–{last["opponent_points"]}'
        item["result"]=f'{result} by {school}, {score}'
        item["eliminated_by"]=school
        item["score"]=score
        updated+=1
path.write_text(json.dumps(db,ensure_ascii=False,separators=(",",":"))+"\n")
print("NCAA team-years enriched with opponent and score:",updated)
