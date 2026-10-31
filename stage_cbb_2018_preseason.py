"""Stage recovered 2017-18 Torvik preseason ranks without publication.

Reads a fully audited candidate mapping and original CSV. Any change of team/rank,
missing identity or provenance mismatch blocks the staging operation.
Historical-only programs retain historical IDs.
"""
import argparse,csv,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--csv",type=Path,required=True)
 p.add_argument("--audit",type=Path,required=True)
 p.add_argument("--output",type=Path,default=Path("cbb/match-lab/imports/preseason-review/2018-staged-preseason.json"))
 args=p.parse_args()
 audit=json.loads(args.audit.read_text())
 mapped=audit["mapped"];legacy=audit["historical_only"]
 if audit["season"]!=2018 or audit["unresolved"] or audit["ambiguous"] or len(mapped)+len(legacy)!=351:
  raise ValueError("Incomplete 2018 registry audit")
 ranked={}
 with args.csv.open(newline="") as file:
  for row in csv.DictReader(file):
   rank=int(row["rank"])
   if int(row["season"])!=2018 or rank in ranked:raise ValueError("Invalid candidate ranks")
   ranked[rank]=row
 if set(ranked)!=set(range(1,352)):raise ValueError("Missing or extra ranks")
 schools=[]
 for entry in mapped+legacy:
  source=ranked[entry["rank"]]
  if source["team"]!=entry["team"]:raise ValueError("Candidate rank/team mismatch")
  identifier=entry.get("slug") or entry.get("historical_id")
  schools.append({"rank":entry["rank"],"team":entry["team"],"team_id":identifier})
 schools.sort(key=lambda x:x["rank"])
 captures={(ranked[i].get("capture_timestamp"),ranked[i]["source_url"]) for i in ranked}
 if len(captures)!=1:raise ValueError("Candidates came from multiple source captures")
 timestamp,url=captures.pop()
 result={"season":2018,"source_name":"Bart Torvik original preseason projection candidate",
         "source_url":url,"capture_timestamp":timestamp,"source_capture_after_season":True,
         "source_provenance_verified":False,"redistribution_permission_verified":False,
         "publication_allowed":False,"rankings":schools}
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(result,indent=2)+"\n")
 print("STAGED ONLY:",len(schools),"preseason candidates;",len(mapped),"registry teams,",len(legacy),"historical-only")
 print("Capture:",timestamp,url)
 print("Source provenance & redistribution approval required before website publication")
if __name__=="__main__":main()
