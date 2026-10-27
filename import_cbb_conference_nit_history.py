"""Import historical CBB conference tournament and NIT finishes from game-level CSV.
Keeps existing curated fields and leaves unmatched records untouched.
"""
import csv,io,json,re,urllib.request
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE="https://huggingface.co/Jensen-holm/Nigl/resolve/main/data/"
def read(name):
    """Prefer local fixtures; provide explicit file-level failures, not an opaque exit code."""
    local=ROOT/"data/cbb/import-source"/name
    if local.is_file():
        body=local.read_text(encoding="utf-8-sig")
    else:
        urls=[BASE+name,BASE+name+"?download=true"]
        errors=[]
        for url in urls:
            try:
                print("Fetching",name,"from",url,flush=True)
                req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 BetWiseArchive/1.0","Accept":"text/csv,*/*"})
                with urllib.request.urlopen(req,timeout=18) as response:
                    body=response.read().decode("utf-8-sig")
                break
            except Exception as exc:
                errors.append(f"{url}: {type(exc).__name__}: {exc}")
        else:
            raise RuntimeError(f"Unable to retrieve {name}; "+ "; ".join(errors))
    rows=list(csv.DictReader(io.StringIO(body)))
    if not rows:raise RuntimeError("Source has no records: "+name)
    print("Loaded",name,len(rows),"rows; columns",list(rows[0]),flush=True)
    return rows
def norm(s):return re.sub(r"[^a-z0-9]","",str(s).lower())
def main():
    teams=read("MTeams.csv"); conf_games=read("MConferenceTourneyGames.csv")
    nit=read("MSecondaryTourneyCompactResults.csv")
    compact=read("MRegularSeasonCompactResults.csv")
    registry=json.loads((ROOT/"data/sports/team-registry.json").read_text())
    byname=defaultdict(set)
    for t in registry["teams"]:
        if t["sport"]!="cbb":continue
        for k in (t.get("name",""),t.get("short_name",""),t["slug"].replace("-"," ")):
            n=norm(k)
            if n:byname[n].add(t["slug"])
    byid={}
    corrections={"duke":"duke-blue-devils","uconn":"uconn-huskies","stjohns":"st-johns-red-storm","northcarolina":"north-carolina-tar-heels"}
    for t in teams:
        n=norm(t["TeamName"]); slugs=byname.get(n,set())
        if n in corrections:slugs={corrections[n]}
        if len(slugs)==1:byid[t["TeamID"]]=next(iter(slugs))
    season_conf=defaultdict(list)
    for r in conf_games:
        year=int(r["Season"])
        if 2016<=year<=2026 and year!=2020:
            season_conf[(r["Season"],r["ConfAbbrev"])].append(r)
    scores={(r["Season"],r["DayNum"],r["WTeamID"],r["LTeamID"]):r for r in compact}
    cp=ROOT/"data/cbb/conference-tournament-results.json"
    cdb=json.loads(cp.read_text()); cdb.setdefault("seasons",{})
    count=0
    for (year,conf),games in season_conf.items():
        games=sorted(games,key=lambda r:int(r["DayNum"]))
        last=games[-1]
        champion=last["WTeamID"]
        # A team's final recorded loss is its elimination; identify round by remaining rounds.
        for teamid in set(x for g in games for x in (g["WTeamID"],g["LTeamID"])):
            slug=byid.get(teamid)
            if not slug:continue
            previous=cdb["seasons"].setdefault(year,{}).get(slug,{})
            if previous.get("result"):continue
            played=[g for g in games if teamid in (g["WTeamID"],g["LTeamID"])]
            if teamid==champion:
                title=f"{conf} Tournament Champion"
                game=last;opponent=byid.get(game["LTeamID"],game["LTeamID"])
                score=scores.get((year,game["DayNum"],game["WTeamID"],game["LTeamID"]))
                if score:title+=f" — Defeated {opponent}, {score['WScore']}–{score['LScore']}"
            else:
                losses=[g for g in played if g["LTeamID"]==teamid]
                if not losses:continue
                game=losses[-1]
                later=len({int(g["DayNum"]) for g in games if int(g["DayNum"])>int(game["DayNum"])})
                rd="Final" if later==0 else "Semifinals" if later==1 else "Quarterfinals" if later==2 else f"Earlier Round"
                opponent=byid.get(game["WTeamID"],game["WTeamID"])
                title=f"Eliminated in {rd} of {conf} Tournament — Lost to {opponent}"
                score=scores.get((year,game["DayNum"],game["WTeamID"],game["LTeamID"]))
                if score:title+=f", {score['LScore']}–{score['WScore']}"
            cdb["seasons"][year][slug]={**previous,"result":title,"source":"Kaggle MConferenceTourneyGames historical archive"}
            count+=1
    cp.write_text(json.dumps(cdb,separators=(",",":"),ensure_ascii=False)+"\n")
    np=ROOT/"data/cbb/tournament-results.json";ndb=json.loads(np.read_text())
    nit_rows=defaultdict(list)
    for r in nit:
        if r["SecondaryTourney"]=="NIT" and 2016<=int(r["Season"])<=2026 and int(r["Season"])!=2020:
            for teamid in (r["WTeamID"],r["LTeamID"]):
                nit_rows[(r["Season"],teamid)].append(r)
    nit_count=0
    for (year,teamid),games in nit_rows.items():
        slug=byid.get(teamid)
        if not slug:continue
        previous=ndb["seasons"].setdefault(year,{}).get(slug,{})
        if previous.get("tournament") in ("NCAA","NIT"):continue
        wins=sum(g["WTeamID"]==teamid for g in games)
        losses=sorted((g for g in games if g["LTeamID"]==teamid),key=lambda g:int(g["DayNum"]))
        if losses:
            last=losses[-1];opponent=byid.get(last["WTeamID"],last["WTeamID"])
            finish="NIT Runner-up" if wins>=4 else "NIT Semifinals" if wins==3 else "NIT Quarterfinals" if wins==2 else "NIT Second Round" if wins==1 else "NIT First Round"
            result=f"Eliminated in {finish} — Lost to {opponent}, {last['LScore']}–{last['WScore']}"
        else: result="NIT Champion"
        ndb["seasons"][year][slug]={**previous,"tournament":"NIT","wins":wins,"result":result,"source":"Kaggle MSecondaryTourneyCompactResults historical archive"}
        nit_count+=1
    np.write_text(json.dumps(ndb,separators=(",",":"),ensure_ascii=False)+"\n")
    print("Conference tournament records:",count,"NIT records:",nit_count,"team IDs matched:",len(byid))
if __name__=="__main__":main()
