#!/usr/bin/env python3
"""Import user-authorized Fourth and Short advanced team stats snapshots.
Research-only. Never silently substitute CFBD metrics or touch production.
Usage: python import_fourthandshort_units.py --input PATH --season 2026 --through-week 6
Input CSV: team,unit,ppa,success_rate,explosiveness (one row per team/unit)
unit: PO, PD, RO, RD. Source data must be an explicitly dated full-field export.
"""
import argparse,csv,json,math,statistics
from collections import defaultdict
from pathlib import Path
K=("PO","PD","RO","RD")
ALIASES={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
def normalize_team(t):return ALIASES.get(t.strip(),t.strip())
def parse_value(s):
 try:
  v=float(str(s).strip().rstrip("%"))
  if not math.isfinite(v):raise ValueError()
  return v
 except Exception:raise ValueError("Non-numeric or missing metric value: "+repr(s))
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",type=Path,required=True);p.add_argument("--season",type=int,required=True)
 p.add_argument("--through-week",type=int,required=True);p.add_argument("--source-url",default="https://fourthandshort.com/team-stats/passing-advanced")
 a=p.parse_args()
 folder=Path("data/research")/str(a.season)
 manifest=folder/"conference_membership.json"
 if not manifest.exists():raise SystemExit("Missing FBS membership: "+str(manifest))
 members=json.loads(manifest.read_text())["teams"]
 teams={normalize_team(t) for t in members if t not in ("Sacramento State","North Dakota State")}
 data={}
 with a.input.open(newline="") as f:
  rd=csv.DictReader(f)
  required={"team","unit","ppa","success_rate","explosiveness"}
  if not required.issubset(rd.fieldnames or []):raise SystemExit("Missing required columns "+str(required-set(rd.fieldnames or [])))
  for row in rd:
   t=normalize_team(row["team"]);k=row["unit"].strip().upper()
   if t not in teams:raise SystemExit("Unknown FBS team: "+t)
   if k not in K:raise SystemExit("Unknown unit "+k)
   key=(t,k)
   if key in data:raise SystemExit("Duplicate team/unit "+str(key))
   ppa=parse_value(row["ppa"])
   success=parse_value(row["success_rate"])
   if success>1.:success/=100.
   if not 0<=success<=1:raise SystemExit("Invalid success_rate for "+str(key))
   expl=parse_value(row["explosiveness"])
   data[key]={"team":t,"unit":k,"ppa":ppa,"success_rate":success,"explosiveness":expl}
 expected={(t,k) for t in teams for k in K}
 missing=expected-set(data)
 if missing:raise SystemExit("INCOMPLETE snapshot: "+str(len(data))+"/"+str(len(expected))+" required team-units; missing "+repr(sorted(missing)[:15]))
 # Source-level snapshot only, NOT a weekly historical reconstruction.
 out=folder/"fourthandshort_inputs"/f"snapshot_week_{a.through_week:02d}.csv"
 out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():raise SystemExit("Snapshot already exists; preserve old file and compare before replacement: "+str(out))
 with out.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=["season","through_week","team","unit","ppa","success_rate","explosiveness"])
  w.writeheader()
  for t,k in sorted(expected):w.writerow({"season":a.season,"through_week":a.through_week,**data[t,k]})
 metadata={"season":a.season,"through_week":a.through_week,"source":a.source_url,
           "coverage":{"teams":len(teams),"units":len(K),"rows":len(data)},
           "status":"source snapshot imported, not yet used by any published dominance model",
           "warning":"This is a dated aggregate team-stat snapshot, NOT independently verified weekly historical data. Do not infer earlier weeks from this snapshot.",
           "scope":"Research branch only. Existing original weekly archives are preserved."}
 out.with_suffix(".json").write_text(json.dumps(metadata,indent=2))
 print("Validated full Fourth and Short input",out,len(data),"unit rows")
if __name__=="__main__":main()
