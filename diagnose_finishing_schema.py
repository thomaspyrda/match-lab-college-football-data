#!/usr/bin/env python3
"""Inspect CFBD advanced-game schema for the finishing-opportunity source field."""
import json, os, urllib.parse, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
KEY=os.environ.get("CFBD_API_KEY")
if not KEY: raise SystemExit("CFBD_API_KEY secret required")
url="https://api.collegefootballdata.com/stats/game/advanced?"+urllib.parse.urlencode({"year":2025,"seasonType":"regular","excludeGarbageTime":"true"})
req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"MatchLab/1.0"})
with urllib.request.urlopen(req,timeout=180) as r:data=json.load(r)
sample=next((x for x in data if x.get("offense")),None) or {}
o=sample.get("offense") or {}
report={"sample_team":sample.get("team"),"offense_keys":sorted(o.keys()),
 "candidate_finishing_fields":{k:o.get(k) for k in o if any(s in k.lower() for s in ("opportun","finish","point"))},
 "pointsPerOpportunity_present":"pointsPerOpportunity" in o,"totalOpportunities_present":"totalOpportunities" in o}
out=ROOT/"data"/"experiments"/"finishing_schema_diagnostic.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2))
