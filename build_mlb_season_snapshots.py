#!/usr/bin/env python3
"""Build verified MLB season snapshots from MLB Stats API. No odds or fabricated values."""
import argparse, json, urllib.request, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
IDS={
108:"los-angeles-angels",109:"arizona-diamondbacks",110:"baltimore-orioles",111:"boston-red-sox",
112:"chicago-cubs",113:"cincinnati-reds",114:"cleveland-guardians",115:"colorado-rockies",
116:"detroit-tigers",117:"houston-astros",118:"kansas-city-royals",119:"los-angeles-dodgers",
120:"washington-nationals",121:"new-york-mets",133:"athletics",134:"pittsburgh-pirates",
135:"san-diego-padres",136:"seattle-mariners",137:"san-francisco-giants",138:"st-louis-cardinals",
139:"tampa-bay-rays",140:"texas-rangers",141:"toronto-blue-jays",142:"minnesota-twins",
143:"philadelphia-phillies",144:"atlanta-braves",145:"chicago-white-sox",146:"miami-marlins",
147:"new-york-yankees",158:"milwaukee-brewers"
}
def fetch(season):
    url=f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={season}&gameType=R"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"BetWiseResearch/1.0"}),timeout=90) as response:
                return json.load(response),url
        except Exception:
            if attempt==2: raise
            time.sleep(2**attempt)
def blank(team,year):
    return {"team_id":team,"season":year,"status":"not_loaded","games_played":0,
            "wins":0,"losses":0,"ties":0,"home":{"wins":0,"losses":0,"ties":0},
            "away":{"wins":0,"losses":0,"ties":0},"runs_scored":0,"runs_allowed":0,
            "runs_per_game":None,"runs_allowed_per_game":None,
            "ats_record":None,"ou_record":None,"source":None}
def build(years):
    result={"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),
            "source":"MLB Stats API (official regular season schedules)","seasons":{}}
    for year in years:
        doc,url=fetch(year)
        rows={slug:blank(team,year) for team,slug in IDS.items()}
        seen=set()
        for day in doc.get("dates",[]):
            for game in day.get("games",[]):
                gid=game.get("gamePk")
                if gid in seen: continue
                seen.add(gid)
                if game.get("gameType")!="R": continue
                status=game.get("status",{}).get("abstractGameState")
                if status!="Final": continue
                teams=game.get("teams",{})
                h,a=teams.get("home",{}),teams.get("away",{})
                hid,aid=h.get("team",{}).get("id"),a.get("team",{}).get("id")
                if hid not in IDS or aid not in IDS: continue
                hs,ass=h.get("score"),a.get("score")
                if not isinstance(hs,int) or not isinstance(ass,int): continue
                for tid,site,rs,ra in ((hid,"home",hs,ass),(aid,"away",ass,hs)):
                    row=rows[IDS[tid]]
                    row["games_played"]+=1;row["runs_scored"]+=rs;row["runs_allowed"]+=ra
                    field="wins" if rs>ra else "losses" if rs<ra else "ties"
                    row[field]+=1;row[site][field]+=1
        for row in rows.values():
            gp=row["games_played"]
            if gp:
                row["status"]="partial" if year==datetime.now(timezone.utc).year else "complete"
                row["runs_per_game"]=round(row["runs_scored"]/gp,1)
                row["runs_allowed_per_game"]=round(row["runs_allowed"]/gp,1)
                row["source"]=url
            assert row["wins"]+row["losses"]+row["ties"]==gp
            assert sum(row[x][y] for x in ("home","away") for y in ("wins","losses","ties"))==gp
        # Every scheduled completed game must contribute exactly two team appearances.
        assert sum(r["games_played"] for r in rows.values())%2==0
        result["seasons"][str(year)]={slug:row for slug,row in rows.items()}
        print(year,len(seen),"scheduled records",sum(r["games_played"] for r in rows.values())//2,"completed games")
    return result
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--years",nargs="+",type=int,default=list(range(2015,2027)));args=parser.parse_args()
    result=build(args.years)
    path=ROOT/"data/mlb/season-snapshots.json";path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        old=json.loads(path.read_text())
        result["seasons"]={**old.get("seasons",{}),**result["seasons"]}
    path.write_text(json.dumps(result,separators=(",",":"),ensure_ascii=False)+"\n")
    print("Saved",path,len(result["seasons"]),"seasons")
if __name__=="__main__":main()
