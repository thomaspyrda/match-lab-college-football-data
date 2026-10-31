"""Inspect available archived 2017/2018 Torvik preseason pages; no publication."""
import json,urllib.request,csv
from pathlib import Path
from audit_cbb_torvik_original_preseason import parse
root=Path("cbb/match-lab/imports/preseason-review")
inventory=json.loads((root/"wayback-captures.json").read_text()) if (root/"wayback-captures.json").exists() else {}
# Inventory is an artifact from an earlier run; retrieve CDX again when not present.
if not inventory:
 from urllib.parse import urlencode
 for year in (2017,2018):
  url=f"https://barttorvik.com/trankpure{year%100:02d}.php"
  endpoint="https://web.archive.org/cdx/search/cdx?"+urlencode({"url":url,"output":"json","filter":"statuscode:200","collapse":"timestamp:6","fl":"timestamp,original,statuscode"})
  try:
   with urllib.request.urlopen(endpoint,timeout=20) as f:rows=json.load(f)[1:]
   inventory[str(year)]=[{"timestamp":r[0],"snapshot":"https://web.archive.org/web/"+r[0]+"id_/"+r[1]} for r in rows]
  except Exception as e:print(year,"CDX error",str(e))
root.mkdir(parents=True,exist_ok=True)
report={}
for year,items in inventory.items():
 if not isinstance(items,list) or not items:continue
 report[year]=[]
 for item in items:
  url=item["snapshot"];url=url.replace("/http","id_/http") if "/id_/http" not in url else url
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=30) as f:html=f.read().decode("utf-8","replace")
   ranked=parse(html)
   unique={r:t for r,t in ranked}
   if year=="2018" and len(unique)>=300:
    with (root/"2018-candidate-rankings.csv").open("w",newline="") as output:
     writer=csv.writer(output)
     writer.writerow(["season","team","rank","source_url","capture_timestamp"])
     for rank,team in sorted(unique.items()):
      writer.writerow([year,team,rank,url,item.get("timestamp","")])
    print("2018 candidate rankings saved for source review")
   result={"capture":url,"ranked_count":len(unique),"top_3":list(sorted(unique.items()))[:3],"complete":len(unique)>=300}
  except Exception as e:result={"capture":url,"error":str(e)}
  report[year].append(result)
  print(year,result)
(root/"capture-review.json").write_text(json.dumps(report,indent=2))
