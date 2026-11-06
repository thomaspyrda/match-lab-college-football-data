"""Build historical NCAA men's basketball team metric ranks from archived seasons.
Rank within the available teams for each season; missing values remain missing.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data/cbb/teams"
OUT=ROOT/"data/cbb/metric-ranks.json"
SUPPLEMENT=ROOT/"data/cbb/opponent-metrics.json"
FIELDS={"avgPoints":"PPG","avgRebounds":"REB/G","avgAssists":"AST/G","avgTurnovers":"TOV/G","avgSteals":"STL/G","avgBlocks":"BLK/G","fieldGoalPct":"FG%","twoPointFieldGoalPct":"2P%","threePointFieldGoalPct":"3P%","freeThrowPct":"FT%","ppgAllowed":"PPG Allowed","offRating":"OFF Rating","defRating":"DEF Rating","pace":"Pace","efg":"eFG%","reboundShare":"Rebound Share%"}
LOWER={"avgTurnovers","ppgAllowed","defRating"}
FIELDS.update({"Points in the Paint":"Points in the Paint","Points in the Paint Allowed":"Points in the Paint Allowed","3P Rate":"3P Rate","3P Rate Allowed":"3P Rate Allowed","FT Attempt Rate":"FT Attempt Rate","Rebounds Allowed/Game":"Rebounds Allowed/Game","Turnover Margin":"Turnover Margin","FG% Allowed":"FG% Allowed","eFG% Allowed":"eFG% Allowed","2P% Allowed":"2P% Allowed","3P% Allowed":"3P% Allowed","FT% Allowed":"FT% Allowed","FT Attempt Rate Allowed":"FT Attempt Rate Allowed","AST/G Allowed":"AST/G Allowed","Defensive Rebound Rate":"Defensive Rebound Rate"})
LOWER.update(["Points in the Paint Allowed","3P Rate Allowed","Rebounds Allowed/Game","FG% Allowed","eFG% Allowed","2P% Allowed","3P% Allowed","FT% Allowed","FT Attempt Rate Allowed","AST/G Allowed"])
def main():
    supplemental=json.loads(SUPPLEMENT.read_text()).get("seasons",{}) if (ROOT/"data/cbb/opponent-metrics.json").exists() else {}
    seasons={}
    total_by_season={}
    registry=json.loads((ROOT/"data/sports/team-registry.json").read_text())
    registered=sum(t["sport"]=="cbb" for t in registry["teams"])
    for path in sorted(DATA.glob("*.json")):
        d=json.loads(path.read_text())
        for y,s in d.get("seasons",{}).items():
            total_by_season[y]=total_by_season.get(y,0)+1
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
            if m.get("twoPointFieldGoalPct") is None and all(isinstance(m.get(k),(int,float)) for k in ("fieldGoalsMade","threePointFieldGoalsMade","fieldGoalsAttempted","threePointFieldGoalsAttempted")):
                m["twoPointFieldGoalPct"]=ratio(m["fieldGoalsMade"]-m["threePointFieldGoalsMade"],m["fieldGoalsAttempted"]-m["threePointFieldGoalsAttempted"],100)
            m["ppgAllowed"]=ratio(opp,gp)
            m["offRating"]=ratio(m.get("points"),pos,100)
            m["defRating"]=ratio(opp,pos,100)
            m["pace"]=ratio(pos,gp)
            m["efg"]=ratio(m.get("fieldGoalsMade",0)+.5*m.get("threePointFieldGoalsMade",0),m.get("fieldGoalsAttempted"),100) if m.get("fieldGoalsMade") is not None and m.get("threePointFieldGoalsMade") is not None else None
            rebounds=m.get("rebounds") or m.get("totalRebounds")
            differential=m.get("reboundsDifferential")
            opponent_rebounds=m.get("opponentRebounds")
            if opponent_rebounds is None:opponent_rebounds=rebounds-differential if rebounds is not None and differential is not None else None
            m["reboundShare"]=ratio(rebounds,rebounds+opponent_rebounds,100) if opponent_rebounds is not None else None
            m["Points in the Paint"]=ratio(m.get('pointsInPaint'),gp)
            m["Points in the Paint Allowed"]=ratio(m.get('opponentPointsInPaint'),gp)
            m["3P Rate"]=ratio(m.get('threePointFieldGoalsAttempted'),m.get('fieldGoalsAttempted'),100)
            m["3P Rate Allowed"]=ratio(m.get('opponentThreePointFieldGoalsAttempted'),m.get('opponentFieldGoalsAttempted'),100)
            m["FT Attempt Rate"]=ratio(m.get('freeThrowsAttempted'),m.get('fieldGoalsAttempted'),100)
            m["Rebounds Allowed/Game"]=ratio(opponent_rebounds,gp)
            m["Turnover Margin"]=ratio(m.get('opponentTurnovers')-m.get('turnovers') if m.get('opponentTurnovers') is not None and m.get('turnovers') is not None else None,gp)
            m["FG% Allowed"]=ratio(m.get('opponentFieldGoalsMade'),m.get('opponentFieldGoalsAttempted'),100)
            m["eFG% Allowed"]=ratio(m.get('opponentFieldGoalsMade')+.5*m.get('opponentThreePointFieldGoalsMade') if m.get('opponentFieldGoalsMade') is not None and m.get('opponentThreePointFieldGoalsMade') is not None else None,m.get('opponentFieldGoalsAttempted'),100)
            m["2P% Allowed"]=ratio(m.get('opponentFieldGoalsMade')-m.get('opponentThreePointFieldGoalsMade') if m.get('opponentFieldGoalsMade') is not None and m.get('opponentThreePointFieldGoalsMade') is not None else None,m.get('opponentFieldGoalsAttempted')-m.get('opponentThreePointFieldGoalsAttempted') if m.get('opponentFieldGoalsAttempted') is not None and m.get('opponentThreePointFieldGoalsAttempted') is not None else None,100)
            m["3P% Allowed"]=ratio(m.get('opponentThreePointFieldGoalsMade'),m.get('opponentThreePointFieldGoalsAttempted'),100)
            m["FT% Allowed"]=ratio(m.get('opponentFreeThrowsMade'),m.get('opponentFreeThrowsAttempted'),100)
            m["FT Attempt Rate Allowed"]=ratio(m.get('opponentFreeThrowsAttempted'),m.get('opponentFieldGoalsAttempted'),100)
            m["AST/G Allowed"]=ratio(m.get('opponentAssists'),gp)
            m["Defensive Rebound Rate"]=ratio(m.get('rebounds')-m.get('offensiveRebounds') if m.get('rebounds') is not None and m.get('offensiveRebounds') is not None else None,m.get('rebounds')-m.get('offensiveRebounds')+m.get('opponentOffensiveRebounds') if all(m.get(k) is not None for k in ['rebounds','offensiveRebounds','opponentOffensiveRebounds']) else None,100)
            for label,value in supplemental.get(y,{}).get(d["slug"],{}).get("values",{}).items():
                if label in FIELDS and m.get(label) is None:m[label]=value
            seasons.setdefault(y,{})[d["slug"]]=m
    result={}
    for year,teams in seasons.items():
        result[year]={"_total_division_one":registered if int(year)==2027 else total_by_season.get(year,registered)}
        for field in FIELDS:
            vals=sorted(((float(m[field]),slug) for slug,m in teams.items() if isinstance(m.get(field),(float,int))),reverse=field not in LOWER)
            ranks={};last=None;rank=0
            for i,(value,slug) in enumerate(vals,1):
                if value!=last:rank=i;last=value
                ranks[slug]=rank
            result[year][field]={"size":len(vals),"ranks":ranks,"values":{slug:value for value,slug in vals}}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"sources":"ESPN archived regular-season team metrics; national ranks within available archived programs","seasons":result},separators=(",",":"))+"\n")
    print("Historical CBB metric ranks:",len(result),"seasons")
if __name__=="__main__":main()
