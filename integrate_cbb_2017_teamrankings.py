"""Import audited 2016-17 TeamRankings numerical preseason ranks without replacing other years."""
import argparse,json
from pathlib import Path
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--audit",type=Path,required=True)
 p.add_argument("--destination",type=Path,default=Path("cbb/match-lab/data/preseason-ranks.json"))
 a=p.parse_args()
 data=json.loads(a.audit.read_text())
 rows=data.get("mapped",[])
 if data.get("season")!=2017 or data.get("rankings_extracted")!=351 or len(rows)!=351 or data.get("unresolved") or data.get("ambiguous"):
  raise ValueError("Audited 2016-17 rankings are incomplete")
 if {int(x["rank"]) for x in rows}!=set(range(1,352)):
  raise ValueError("2016-17 ranks must be uniquely numbered 1 through 351")
 current=json.loads(a.destination.read_text())
 ranks={};historical=[]
 for x in rows:
  ident=x["slug"];rank=int(x["rank"])
  if ident.startswith("historical:"):
   historical.append({"historical_id":ident,"rank":rank})
  else:
   if ident in ranks:raise ValueError(f"Duplicate school identity: {ident}")
   ranks[ident]={"rank":rank,"source":"TeamRankings 2016-17 preseason rankings"}
 if len(ranks)+len(historical)!=351:
  raise ValueError("2016-17 import lost rankings")
 old=current.setdefault("seasons",{}).get("2017")
 if old and old!=ranks:raise ValueError("Conflicting 2017 ranks already exist")
 current["seasons"]["2017"]=ranks
 existing=current.setdefault("historical_only",{}).get("2017")
 if existing and existing!=historical:raise ValueError("Conflicting historical-only 2017 ranks")
 current["historical_only"]["2017"]=historical
 current.setdefault("source_notes",{})["2017"]={"source":"TeamRankings 2016-17 preseason ranking article","source_url":data["source"],"scope":"original preseason ranks, not season-end standings"}
 a.destination.write_text(json.dumps(current,indent=2)+"\n")
 print(f"Imported 2016-17 preseason rankings: {len(ranks)} registry teams, {len(historical)} historical identities")
if __name__=="__main__":main()
