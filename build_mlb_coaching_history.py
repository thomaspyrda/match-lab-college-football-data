#!/usr/bin/env python3
"""Resolve 2015–2025 MLB managerial tenures from the saved, audited assignments.
No incomplete manager names are published. 2026 and assistant coaches remain pending.
"""
import argparse,csv,io,json,urllib.request,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"data/mlb/manager-source-records.json"
OUT=ROOT/"data/mlb/coaching-history.json"
URL="https://raw.githubusercontent.com/corbtastik/lahman-baseball-db/main/People.csv"
def names_from_people():
    req=urllib.request.Request(URL,headers={"User-Agent":"BetWiseSportsResearch/1.0","Accept":"text/csv"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=100) as response:
                raw=response.read()
            if len(raw)<100000:raise ValueError("People.csv appears truncated")
            rows=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            return {r["playerID"]:" ".join(filter(None,[r.get("nameFirst"),r.get("nameLast")])).strip() for r in rows}
        except Exception:
            if attempt==3:raise
            time.sleep(2**attempt)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--people-file",type=Path,help="Optional local People.csv file")
    args=ap.parse_args()
    raw=json.loads(SOURCE.read_text())
    people=({r["playerID"]:" ".join(filter(None,[r.get("nameFirst"),r.get("nameLast")])).strip() for r in csv.DictReader(args.people_file.open(encoding="utf-8-sig"))} if args.people_file else names_from_people())
    out={}
    for slug,seasons in raw["teams"].items():
        out[slug]={}
        for year in range(2015,2027):
            assignments=seasons.get(str(year),[]) if year<=2025 else []
            managers=[]
            for row in assignments:
                name=people.get(row["player_id"])
                if not name:raise ValueError(f"Unresolved manager name {slug} {year}: {row['player_id']}")
                managers.append({"name":name,"player_id":row["player_id"],"order":row["order"],"games":row["games"],"wins":row["wins"],"losses":row["losses"],"source":raw["source"]})
            if year<=2025 and not managers:raise ValueError(f"Missing manager for {slug} {year}")
            out[slug][str(year)]={"managers":managers,"hitting_coaches":[],"pitching_coaches":[],"staff_status":"managers_only" if managers else "not_loaded"}
    assert len(out)==30
    n=sum(len(t[str(y)]["managers"]) for t in out.values() for y in range(2015,2026))
    assert n==389,f"Unexpected managerial assignment count: {n}"
    data={"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),"source":raw["source"],"names_source":URL,"coverage":"2015–2025 managerial tenures; 2026 and hitting/pitching coaches not yet verified","teams":out}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n")
    print(f"Generated {OUT}: {len(out)} teams, 330 team-seasons, {n} manager assignments")
if __name__=="__main__":main()
