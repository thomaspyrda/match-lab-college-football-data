"""Build historical NCAA men's basketball team metric ranks from archived seasons.
Rank within the available teams for each season; missing values remain missing.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data/cbb/teams"
OUT=ROOT/"data/cbb/metric-ranks.json"
FIELDS={"avgPoints":"PPG","avgRebounds":"REB/G","avgAssists":"AST/G","avgTurnovers":"TOV/G","avgSteals":"STL/G","avgBlocks":"BLK/G","fieldGoalPct":"FG%","threePointFieldGoalPct":"3P%","freeThrowPct":"FT%"}
LOWER={"avgTurnovers"}
def main():
    seasons={}
    for path in sorted(DATA.glob("*.json")):
        d=json.loads(path.read_text())
        for y,s in d.get("seasons",{}).items():
            p=s.get("phases",{}).get("regular",{})
            if p.get("completed_games",0)<1:continue
            m=p.get("metrics",{})
            if not m:continue
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
