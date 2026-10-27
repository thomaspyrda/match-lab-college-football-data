"""Build Division I CBB season leaders from saved ESPN team-player archives.
Only the requested historical seasons are published; no network dependency.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CATS={"points":"Points","avgPoints":"Points Per Game","rebounds":"Rebounds","avgRebounds":"Rebounds Per Game","assists":"Assists","avgAssists":"Assists Per Game","steals":"Steals","avgSteals":"Steals Per Game","blocks":"Blocks","avgBlocks":"Blocks Per Game","fieldGoalPct":"Field Goal %","threePointFieldGoalPct":"3-Point %","freeThrowPct":"Free Throw %","avgMinutes":"Minutes Per Game"}
RATE={"avgPoints","avgRebounds","avgAssists","avgSteals","avgBlocks","fieldGoalPct","threePointFieldGoalPct","freeThrowPct","avgMinutes"}
def main():
    seasons={}
    team_count=0
    for path in sorted((ROOT/"data/cbb/teams").glob("*.json")):
        data=json.loads(path.read_text());team_count+=1
        for year,season in data.get("seasons",{}).items():
            if not 2016<=int(year)<=2026:continue
            for player in season.get("players",[]):
                stats=player.get("stats") or {}
                if not player.get("name") or not isinstance(stats,dict):continue
                gp=stats.get("gamesPlayed")
                if not isinstance(gp,(int,float)) or gp<1:continue
                row={"name":player["name"],"team":data["slug"],"id":str(player.get("id") or ""),"gp":gp}
                for metric in CATS:
                    value=stats.get(metric)
                    if isinstance(value,(int,float)) and not isinstance(value,bool):
                        # Avoid misleading percentages from players with one appearance.
                        if metric in RATE and gp<10:continue
                        seasons.setdefault(year,{}).setdefault(metric,[]).append(dict(row,value=round(float(value),3)))
    result={}
    for year,categories in seasons.items():
        result[year]={}
        for metric,rows in categories.items():
            rows.sort(key=lambda x:(-x["value"],x["name"],x["team"]))
            result[year][metric]={"label":CATS[metric],"leaders":rows[:10],"eligible":len(rows)}
    output=ROOT/"data/cbb/division-one-season-leaders.json"
    output.write_text(json.dumps({"source":"Saved ESPN team-player season archives; rate statistics require >=10 games","seasons":result},separators=(",",":"),ensure_ascii=False)+"\n")
    print("D1 season leaders:",team_count,"teams",len(result),"seasons")
if __name__=="__main__":main()
