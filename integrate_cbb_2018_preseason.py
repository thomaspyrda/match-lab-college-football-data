"""Build the existing CBB Match Lab preseason-ranks input from audited 2018 candidates.

Only numerical ranks and internal team identifiers enter the Match Lab.
Other seasons and their rankings are retained unchanged.
"""
import argparse,json
from pathlib import Path

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--staged",type=Path,required=True)
 parser.add_argument("--destination",type=Path,default=Path("cbb/match-lab/data/preseason-ranks.json"))
 args=parser.parse_args()
 staged=json.loads(args.staged.read_text())
 if staged.get("season")!=2018 or not staged.get("working_preseason_baseline_accepted"):
  raise ValueError("Missing explicit 2018 baseline approval")
 rows=staged["rankings"]
 if len(rows)!=351 or {r["rank"] for r in rows}!=set(range(1,352)):
  raise ValueError("Incomplete or duplicate preseason ranks")
 current=json.loads(args.destination.read_text()) if args.destination.exists() else {"seasons":{}}
 seasons=current.setdefault("seasons",{})
 # Re-runs idempotent; never change previously published 2018 values silently.
 wanted={}
 legacy=[]
 for row in rows:
  identifier=row["team_id"]
  if identifier.startswith("historical:"):
   legacy.append({"historical_id":identifier,"rank":row["rank"]})
  else:
   wanted[identifier]={"rank":row["rank"],"source":"Bart Torvik 2017-18 preseason projection archive"}
 existing=seasons.get("2018")
 if existing and existing!=wanted:
  raise ValueError("2018 preseason values already exist and differ; refusing overwrite")
 seasons["2018"]=wanted
 current.setdefault("historical_only",{})["2018"]=legacy
 current.setdefault("source_notes",{})["2018"]={
  "source":"Bart Torvik original preseason page archived via Internet Archive",
  "source_url":staged["source_url"],"capture_timestamp":staged["capture_timestamp"],
  "source_values_assumed_unchanged":True,
  "scope":"preseason numerical rankings only; not BetWise strength or efficiency"
 }
 args.destination.parent.mkdir(parents=True,exist_ok=True)
 args.destination.write_text(json.dumps(current,indent=2)+"\n")
 print(f"2018 ranks prepared: {len(wanted)} current-registry, {len(legacy)} historical-only; existing seasons retained.")
if __name__=="__main__":main()
