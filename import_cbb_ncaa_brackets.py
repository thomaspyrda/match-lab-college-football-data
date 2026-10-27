"""Apply NCAA tournament finishes from historical bracket records to CBB team archives.
Source records are team, seed, NCAA tournament wins, one text file per year.
Do not change team archives, NIT results, or conference results.
"""
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"data/cbb/tournament-results.json"
REMOTE="https://raw.githubusercontent.com/possibly-wrong/ncaa-tournament/master/"
OVERRIDES={"duke":"duke-blue-devils","connecticut":"uconn-huskies","stjohns":"st-johns-red-storm","northcarolina":"north-carolina-tar-heels","michiganst":"michigan-state-spartans","ohiost":"ohio-state-buckeyes","iowast":"iowa-state-cyclones","utahst":"utah-state-aggies","vcu":"vcu-rams"}
def normalize(v):return re.sub("[^a-z0-9]","",str(v).lower().replace("university",""))
def finish(w):
    return {0:"NCAA Tournament · Round of 64",1:"NCAA Tournament · Round of 32",2:"NCAA Tournament · Sweet 16",3:"NCAA Tournament · Elite Eight",4:"NCAA Tournament · Final Four",5:"NCAA Tournament · National Runner-up",6:"NCAA Tournament · National Champion"}.get(w)
def main():
    registry=json.loads((ROOT/"data/sports/team-registry.json").read_text())
    byname={}
    for team in registry["teams"]:
        if team["sport"]!="cbb":continue
        slug=team["slug"]
        for name in [slug,team.get("name",""),team.get("display_name",""),team.get("short_name","")]:
            key=normalize(name.replace("-",""))
            if key:byname.setdefault(key,set()).add(slug)
    for k,v in OVERRIDES.items():byname[normalize(k)]={v}
    db=json.loads(OUT.read_text());totals=0
    for year in range(2016,2027):
        if year==2020:continue
        try:
            with urllib.request.urlopen(REMOTE+str(year)+".txt",timeout=25) as response:
                lines=response.read().decode().splitlines()
        except Exception as e:print(year,"unavailable",e);continue
        found=0;ambiguous=[]
        for line in lines:
            parts=line.strip().split()
            if len(parts)!=3:continue
            try:wins=int(parts[2]);seed=int(parts[1])
            except ValueError:continue
            if not 0<=wins<=6 or not 1<=seed<=16:continue
            key=normalize(parts[0]);slugs=byname.get(key,set())
            if len(slugs)!=1:
                ambiguous.append(parts[0]);continue
            slug=next(iter(slugs))
            record=db["seasons"].setdefault(str(year),{}).get(slug,{})
            if record.get("tournament") in ("NIT","canceled","NCAA"):continue
            db["seasons"][str(year)][slug]={"tournament":"NCAA","result":finish(wins),"wins":wins,"seed":seed,"source":"Historical NCAA tournament bracket (possibly-wrong/ncaa-tournament)"}
            found+=1
        totals+=found
        print(year,"NCAA teams matched",found,"unmapped",len(ambiguous),",".join(ambiguous[:20]))
    OUT.write_text(json.dumps(db,separators=(",",":"),ensure_ascii=False)+"\n")
    print("NCAA results imported",totals)
if __name__=="__main__":main()
