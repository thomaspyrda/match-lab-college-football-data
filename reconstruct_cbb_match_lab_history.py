#!/usr/bin/env python3
"""Reconstruct CBB pregame match data from dated team schedules and archived lines.

All statistics come exclusively from games dated before the target game's date.
Require final scores from BOTH team archives and a documented historical market.
Do not label these unadjusted scoring averages as adjusted efficiencies or rankings.
"""
import json, math
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone, timedelta

ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def number(v):
    try:
        if v is None or v=="":return None
        x=float(v)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None
def stamp(v):
    try:return datetime.fromisoformat(str(v).replace("Z","+00:00"))
    except (TypeError,ValueError):return None
def avg(v):return round(sum(v)/len(v),3) if v else None

def main():
    registry=load(ROOT/"data/sports/team-registry.json")["teams"]
    schools=[x for x in registry if x.get("sport")=="cbb"]
    idmap={str(x["espn_id"]):x for x in schools}
    records=defaultdict(dict)
    odds=defaultdict(dict)
    audits=defaultdict(int)
    for school in schools:
        slug=school["slug"]
        pf=ROOT/f"data/cbb/teams/{slug}.json"
        mf=ROOT/f"data/cbb/markets/{slug}.json"
        if not pf.exists() or not mf.exists():continue
        data=load(pf); markets=load(mf)
        for season,archive in data.get("seasons",{}).items():
            for phase in archive.get("phases",{}).values():
                for game in phase.get("games",[]):
                    if str(game.get("status","")).lower() not in ("final","completed"):continue
                    gdate=stamp(game.get("date"))
                    pts=number(game.get("points")); opppts=number(game.get("opponent_points"))
                    opp=str(game.get("opponent_id") or "")
                    gid=str(game.get("id") or "")
                    if not(gdate and pts is not None and opppts is not None and opp in idmap and gid):continue
                    records[(str(season),slug)][gid]={"date":gdate,"points":pts,"opp_points":opppts,
                      "opponent":idmap[opp]["slug"],"location":game.get("location"),"id":gid}
            for gid,market in markets.get("games",{}).get(str(season),{}).items():
                if isinstance(market,dict):odds[(str(season),str(gid))][slug]=market
    history=[]
    for (season,slug),teamgames in records.items():
        team=next((x for x in schools if x["slug"]==slug),None)
        if team is None:continue
        for gid,game in teamgames.items():
            if game["location"] not in ("Home","Away"):continue
            if game["location"]!="Home":continue
            other=game["opponent"]
            opponent=records.get((season,other),{}).get(gid)
            if not opponent:continue
            if opponent["opponent"]!=slug or opponent["location"]!="Away":continue
            if game["points"]!=opponent["opp_points"] or opponent["points"]!=game["opp_points"]:continue
            markets=odds.get((season,gid),{})
            home_line=markets.get(slug,{});away_line=markets.get(other,{})
            total=number(home_line.get("total"));spread=number(home_line.get("spread"))
            away_total=number(away_line.get("total"));away_spread=number(away_line.get("spread"))
            if None in (total,spread,away_total,away_spread) or total<=0:continue
            if abs(total-away_total)>0.01 or abs(spread+away_spread)>0.01:continue
            # Reject unanchored or post-tip bookmaker observations.
            observed=stamp(home_line.get("observed_at"));observed_away=stamp(away_line.get("observed_at"))
            if not observed or not observed_away or observed>game["date"] or observed_away>game["date"]:continue
            result="over" if game["points"]+opponent["points"]>total else "under" if game["points"]+opponent["points"]<total else "push"
            code={"over":"O","under":"U","push":"P"}[result]
            if home_line.get("ou")!=code or away_line.get("ou")!=code:continue
            def pregame(subject):
                prior=sorted([g for g in records.get((season,subject),{}).values()
                              if g["date"].date()<game["date"].date()],key=lambda g:g["date"])
                if len(prior)<5:return None
                return {"games":len(prior),"ppg":avg([p["points"] for p in prior]),
                        "allowed_ppg":avg([p["opp_points"] for p in prior]),
                        "win_pct":round(sum(p["points"]>p["opp_points"] for p in prior)/len(prior),4),
                        "last5_win_pct":round(sum(p["points"]>p["opp_points"] for p in prior[-5:])/5,4),
                        "margin":avg([p["points"]-p["opp_points"] for p in prior])}
            hp=pregame(slug);ap=pregame(other)
            if hp is None or ap is None:continue
            away_team=next(x for x in schools if x["slug"]==other)
            before_date=(game["date"]-timedelta(seconds=1)).isoformat()
            # The season archive collection timestamp provides a real observation of the final result.\n            # Never invent a result-verification timestamp.\n            final_date=next((v for v in [stamp(load(ROOT/f"data/cbb/teams/{slug}.json")["seasons"][season].get("collected_at"))] if v and v>game["date"]),None)\n            if final_date is None:continue
            # Mark records as reconstructed prior-game profiles, not archived model ratings.
            item={"game_id":gid,"season":int(season),"date":game["date"].isoformat(),
             "snapshot_as_of":before_date,"result_verified_at":final_date.isoformat(),
             "pregame_verified":True,"historical_snapshot_source":"chronological completed prior games from ESPN archived team schedules",
             "pregame_source":f"data/cbb/teams/{slug}.json","result_source":"independently agreeing home and away ESPN team archives",
             "market_source":home_line.get("source") or "archived historical bookmaker lines",
             "away":{"name":away_team["name"],"profile":ap},"home":{"name":team["name"],"profile":hp},
             "market":{"spread":spread,"total":total},
             "result":{"away_points":int(opponent["points"]),"home_points":int(game["points"]),
                       "total":result,"verified":True}}
            history.append(item);audits["eligible"]+=1
    dest=ROOT/"cbb/match-lab/data/verified-historical.json"
    dest.parent.mkdir(parents=True,exist_ok=True)
    history.sort(key=lambda x:(x["date"],x["game_id"]))
    dest.write_text(json.dumps({"schema_version":1,"verified_only":True,"method":"chronological reconstructed pregame scoring profiles","games":history},separators=(",",":"))+"\n")
    print("Eligible verified historical CBB games:",len(history))
if __name__=="__main__":main()
