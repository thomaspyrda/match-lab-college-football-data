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
    collected_at={}
    registry_by_slug={x["slug"]:x for x in schools}
    for school in schools:
        slug=school["slug"]
        pf=ROOT/f"data/cbb/teams/{slug}.json"
        mf=ROOT/f"data/cbb/markets/{slug}.json"
        if not pf.exists() or not mf.exists():continue
        data=load(pf); markets=load(mf)
        for sy, archive in data.get("seasons",{}).items():
            collected_at[(str(sy),slug)]=stamp(archive.get("collected_at"))
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
    box_snapshots={}
    for path in sorted((ROOT/"cbb/match-lab/data").glob("box-pregame-*.json")):
        try:
            for gid,by_team in load(path).get("games",{}).items():box_snapshots[gid]=by_team
        except (ValueError,OSError):continue
    preseason={}
    rank_path=ROOT/"cbb/match-lab/data/preseason-ranks.json"
    if rank_path.exists():preseason=load(rank_path).get("seasons",{})
    history=[]
    for (season,slug),teamgames in records.items():
        team=registry_by_slug.get(slug)
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
            if home_line.get("line_type")!="provider historical line" or away_line.get("line_type")!="provider historical line":continue
            result="over" if game["points"]+opponent["points"]>total else "under" if game["points"]+opponent["points"]<total else "push"
            code={"over":"O","under":"U","push":"P"}[result]
            if home_line.get("ou")!=code or away_line.get("ou")!=code:continue
            def pregame(subject):
                prior=sorted([g for g in records.get((season,subject),{}).values()
                              if g["date"].date()<game["date"].date()],key=lambda g:g["date"])
                if len(prior)<5:return None
                rest_days=(game["date"].date()-prior[-1]["date"].date()).days-1
                return {"games":len(prior),"rest_days":rest_days,"ppg":avg([p["points"] for p in prior]),
                        "allowed_ppg":avg([p["opp_points"] for p in prior]),
                        "win_pct":round(sum(p["points"]>p["opp_points"] for p in prior)/len(prior),4),
                        "last5_win_pct":round(sum(p["points"]>p["opp_points"] for p in prior[-5:])/5,4),
                        "wins":sum(p["points"]>p["opp_points"] for p in prior),
                        "losses":sum(p["points"]<p["opp_points"] for p in prior),
                        "last5_wins":sum(p["points"]>p["opp_points"] for p in prior[-5:]),
                        "last5_losses":sum(p["points"]<p["opp_points"] for p in prior[-5:]),
                        "margin":avg([p["points"]-p["opp_points"] for p in prior])}
            hp=pregame(slug);ap=pregame(other)
            if hp is None or ap is None:continue
            extra=box_snapshots.get(gid,{})
            home_extra=extra.get(str(team["espn_id"]),{})
            away_extra=extra.get(str(registry_by_slug[other]["espn_id"]),{})
            hp.update({k:v for k,v in home_extra.items() if isinstance(v,(int,float))})
            hp.update(dated_ratings(season,team["espn_id"],game["date"]))
            home_rank=preseason.get(str(season),{}).get(slug)
            if home_rank:hp["preseason_rank"]=home_rank["rank"]
            ap.update({k:v for k,v in away_extra.items() if isinstance(v,(int,float))})
            ap.update(dated_ratings(season,registry_by_slug[other]["espn_id"],game["date"]))
            away_rank=preseason.get(str(season),{}).get(other)
            if away_rank:ap["preseason_rank"]=away_rank["rank"]
            away_team=registry_by_slug[other]
            before_date=(game["date"]-timedelta(seconds=1)).isoformat()
            # Require an independently stored postgame archive collection time.
            # Never use the game's own date as a fabricated verification time.
            collected=collected_at.get((season,slug))
            opposing_collection=collected_at.get((season,other))
            if opposing_collection is None or opposing_collection<=game["date"]:continue
            collected=max(collected,opposing_collection) if collected else None
            if collected is None or collected<=game["date"]:continue
            final_date=collected
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
