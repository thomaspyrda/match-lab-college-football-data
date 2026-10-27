"""Build historical NCAA men's basketball team metric ranks from archived seasons.
Rank within the available teams for each season; missing values remain missing.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data/cbb/teams"
OUT=ROOT/"data/cbb/metric-ranks.json"
FIELDS={"avgPoints":"PPG","avgRebounds":"REB/G","avgAssists":"AST/G","avgTurnovers":"TOV/G","avgSteals":"STL/G","avgBlocks":"BLK/G","fieldGoalPct":"FG%","threePointFieldGoalPct":"3P%","freeThrowPct":"FT%","ppgAllowed":"PPG Allowed","offRating":"OFF Rating","defRating":"DEF Rating","pace":"Pace","efg":"eFG%","reboundShare":"Rebound Share%"}
LOWER={"avgTurnovers","ppgAllowed","defRating"}
def main():
    seasons={}
    for path in sorted(DATA.glob("*.json")):
        d=json.loads(path.read_text())
        for y,s in d.get("seasons",{}).items():
            p=s.get("phases",{}).get("regular",{})
            if p.get("completed_games",0)<1:continue
            m=dict(p.get("metrics",{}))
            if not m:continue
            games=[g for g in p.get("games",[]) if g.get("status")=="final"]
            gp=m.get("gamesPlayed") or len(games)
            opp=sum(g.get("opponent_points",0) for g in games if g.get("opponent_points") is not None) if games else None
            pos=None
            required=["fieldGoalsAttempted","offensiveRebounds","turnovers","freeThrowsAttempted"]
            if all(isinstance(m.get(k),(int,float)) for k in required):
                pos=m["fieldGoalsAttempted"]-m["offensiveRebounds"]+m["turnovers"]+.475*m["freeThrowsAttempted"]
            def ratio(a,b,mult=1):
                return a/b*mult if a is not None and isinstance(b,(int,float)) and b>0 else None
            m["ppgAllowed"]=ratio(opp,gp)
            m["offRating"]=ratio(m.get("points"),pos,100)
            m["defRating"]=ratio(opp,pos,100)
            m["pace"]=ratio(pos,gp)
            m["efg"]=ratio(m.get("fieldGoalsMade",0)+.5*m.get("threePointFieldGoalsMade",0),m.get("fieldGoalsAttempted"),100) if m.get("fieldGoalsMade") is not None and m.get("threePointFieldGoalsMade") is not None else None
            rebounds=m.get("rebounds") or m.get("totalRebounds")
            differential=m.get("reboundsDifferential")
            opponent_rebounds=rebounds-differential if rebounds is not None and differential is not None else None
            m["reboundShare"]=ratio(rebounds,rebounds+opponent_rebounds,100) if opponent_rebounds is not None else None
            seasons.setdefault(y,{})[d["slug"]]=m
    result={}
    for year,teams in seasons.items():
        result[year]={}
        for field in FIELDS:
            vals=sorted(((float(m[field]),slug) for slug,m in teams.items() if isinstance(m.get(field),(float,int))),reverse=field not in LOWER)
            ranks={};last=None;rank=0
            for i,(value,slug) in enumerate(vals,1):
                if value!=last:rank=i;last=value
                ranks[slug]=rank
            result[year][field]={"size":len(vals),"ranks":ranks}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"sources":"ESPN archived regular-season team metrics; national ranks within available archived programs","seasons":result},separators=(",",":"))+"\n")
    print("Historical CBB metric ranks:",len(result),"seasons")
if __name__=="__main__":main()
