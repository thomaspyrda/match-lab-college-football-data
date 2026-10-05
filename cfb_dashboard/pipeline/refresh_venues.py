#!/usr/bin/env python3
"""Refresh CFB Dashboard venue metadata from CFBD without touching Match Lab logic."""
import json,os,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data"/"cfb_dashboard_venues.json"
KEY=os.environ.get("CFBD_API_KEY")
if not KEY: raise SystemExit("CFBD_API_KEY secret is required")

req=urllib.request.Request("https://api.collegefootballdata.com/venues",headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"BetWise-CFB-Dashboard/0.1"})
with urllib.request.urlopen(req,timeout=90) as r: rows=json.load(r)
existing={}
if OUT.exists():
    try: existing=json.loads(OUT.read_text(encoding="utf-8")).get("venues",{})
    except Exception: existing={}
venues={}
for v in rows:
    vid=v.get("id")
    if vid is None: continue
    venues[str(vid)]={
      "name":v.get("name"),"city":v.get("city"),"state":v.get("state"),
      "latitude":v.get("latitude"),"longitude":v.get("longitude"),
      "roof":"dome" if v.get("dome") is True else ("outdoors" if v.get("dome") is False else None),
      "source":"cfbd",
    }
for key,value in existing.items():
    if isinstance(value,dict) and value.get("manual_override"):
        venues[key]=venues.get(key,{})|value
OUT.write_text(json.dumps({"schema_version":"1.0","source":"CFBD /venues","venues":venues},indent=2),encoding="utf-8")
print(f"Refreshed {len(venues)} CFB venues")
