"""Discover preserved snapshots of original Torvik preseason projection pages.
Only reports archive captures; does not publish, rank or assume snapshot validity.
"""
import json,urllib.parse,urllib.request
from pathlib import Path
def main():
 out={}
 for year in range(2016,2021):
  url=f"https://barttorvik.com/trankpure{year%100:02d}.php"
  params=urllib.parse.urlencode({"url":url,"output":"json","filter":"statuscode:200","collapse":"timestamp:6","fl":"timestamp,original,statuscode","filter":"mimetype:text/html"})
  endpoint="https://web.archive.org/cdx/search/cdx?"+params
  try:
   req=urllib.request.Request(endpoint,headers={"User-Agent":"BetWise-CBB-History-Audit/1.0"})
   with urllib.request.urlopen(req,timeout=20) as r:data=json.load(r)
   rows=data[1:] if data and data[0][0]=="timestamp" else []
   out[str(year)]=[{"timestamp":row[0],"snapshot":"https://web.archive.org/web/"+row[0]+"/"+row[1]} for row in rows]
  except Exception as e:
   out[str(year)]={"error":f"{type(e).__name__}: {e}"}
  print(year, len(out[str(year)]) if isinstance(out[str(year)],list) else out[str(year)])
 target=Path("cbb/match-lab/imports/preseason-review/wayback-captures.json")
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(out,indent=2)+"\n")
if __name__=="__main__":main()
