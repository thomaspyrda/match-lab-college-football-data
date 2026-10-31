"""Import audited 2018-19 TeamRankings numerical preseason ranks without replacing other years."""
import argparse,json
from pathlib import Path
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--audit",type=Path,required=True)
 p.add_argument("--destination",type=Path,default=Path("cbb/match-lab/data/preseason-ranks.json"))
 a=p.parse_args()
 data=json.loads(a.audit.read_text())
 rows=data.get("mapped",[])
 if data.get("season")!=2019 or data.get("rankings_extracted")!=353 or len(rows)!=353 or data.get("unresolved") or data.get("ambiguous"):
  raise ValueError("Audited 2018-19 rankings are incomplete")
 if {int(x["rank"]) for x in rows}!=set(range(1,354)):
  raise ValueError("2018-19 ranks must be uniquely numbered 1 through 353")
 current=json.loads(a.destination.read_text())
 ranks={};historical=[]
 for x in rows:
  ident=x["slug"];rank=int(x["rank"])
  if ident.startswith("historical:"):
   historical.append({"historical_id":ident,"rank":rank})
  else:
   if ident in ranks:raise ValueError(f"Duplicate school identity: {ident}")
   ranks[ident]={"rank":rank,"source":"TeamRankings 2018-19 preseason rankings"}
 if len(ranks)+len(historical)!=353:
  raise ValueError("2018-19 import lost rankings")
 old=current.setdefault("seasons",{}).get("2019")
 if old and old!=ranks:raise ValueError("Conflicting 2019 ranks already exist")
 current["seasons"]["2019"]=ranks
 existing=current.setdefault("historical_only",{}).get("2019")
 if existing and existing!=historical:raise ValueError("Conflicting historical-only 2019 ranks")
 current["historical_only"]["2019"]=historical
 current.setdefault("source_notes",{})["2019"]={"source":"TeamRankings 2018-19 preseason ranking article","source_url":data["source"],"scope":"original preseason ranks, not season-end standings"}
 a.destination.write_text(json.dumps(current,indent=2)+"\n")
 print(f"Imported 2018-19 preseason rankings: {len(ranks)} registry teams, {len(historical)} historical identities")
if __name__=="__main__":main()
