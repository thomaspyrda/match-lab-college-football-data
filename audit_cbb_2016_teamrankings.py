"""Audit TeamRankings full 2015-16 preseason rank list against CBB registry.
Read-only: produce a review artifact. Never publish partially mapped rankings.
"""
import argparse,json,re,urllib.request
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup
from audit_cbb_2018_preseason_registry import norm,HISTORICAL_SLUGS,ADDITIONAL_HISTORICAL_SLUGS,HISTORICAL_ONLY
URL="https://www.teamrankings.com/blog/ncaa-basketball/college-basketball-preseason-rankings-ratings-for-2015-16"
ROOT=Path(__file__).resolve().parent
def get_rows(html):
 soup=BeautifulSoup(html,"html.parser")
 rows=[]
 for table in soup.select("table"):
  current=[]
  for tr in table.select("tr"):
   cells=[c.get_text(" ",strip=True) for c in tr.find_all(["td","th"],recursive=False)]
   if len(cells)<3 or not re.fullmatch(r"\\d{1,3}",cells[0]):continue
   try:rank=int(cells[0]);rating=float(cells[2])
   except ValueError:continue
   if 1<=rank<=351:current.append({"rank":rank,"team":cells[1],"rating":rating})
  if len(current)>len(rows):rows=current
 if len(rows)!=351 or {r["rank"] for r in rows}!=set(range(1,352)):
  raise ValueError("Full 351-team ranking table missing, incomplete, or duplicated")
 return sorted(rows,key=lambda r:r["rank"])
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--html",type=Path)
 ap.add_argument("--output",type=Path,default=Path("cbb/match-lab/imports/preseason-review/2016-teamrankings-audit.json"))
 args=ap.parse_args()
 if args.html:html=args.html.read_text()
 else:
  req=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 (historical rankings audit)"})
  html=urllib.request.urlopen(req,timeout=25).read().decode("utf-8","replace")
 rows=get_rows(html)
 teams=json.loads((ROOT/"data/sports/team-registry.json").read_text())["teams"]
 registry=[t for t in teams if t.get("sport")=="cbb"]
 aliases=defaultdict(set)
 for t in registry:
  for name in [t.get("name"),t.get("short_name"),t.get("abbreviation"),*(t.get("aliases") or [])]:
   if name:aliases[norm(name)].add(t["slug"])
 # Only explicit known spellings; unresolved names remain unresolved.
 aliases_extra={
  "N Carolina":"north-carolina-tar-heels","W Virginia":"west-virginia-mountaineers",
  "S Methodist":"smu-mustangs","Wichita St":"wichita-state-shockers",
  "Michigan St":"michigan-state-spartans","Iowa State":"iowa-state-cyclones",
  "N Iowa":"northern-iowa-panthers","Geo Wshgtn":"george-washington-revolutionaries",
  "S Carolina":"south-carolina-gamecocks","Ste F Austin":"stephen-f-austin-lumberjacks",
  "E Tenn St":"east-tennessee-state-buccaneers","TN Tech":"tennessee-tech-golden-eagles",
  "High Point":"high-point-panthers","E Kentucky":"eastern-kentucky-colonels"
 }
 known={t["slug"] for t in registry}
 for name,slug in aliases_extra.items():
  if slug in known:aliases[norm(name)].add(slug)
 for name,slug in {**HISTORICAL_SLUGS,**ADDITIONAL_HISTORICAL_SLUGS}.items():
  if slug in known:aliases[norm(name)].add(slug)
 mapped=[];missing=[];ambiguous=[];used=set()
 for row in rows:
  key=norm(row["team"]);options=aliases.get(key,set())
  if len(options)==1:
   slug=next(iter(options))
   if slug in used:ambiguous.append({**row,"reason":"duplicate canonical team","options":[slug]})
   else:mapped.append({**row,"slug":slug});used.add(slug)
  elif len(options)>1:ambiguous.append({**row,"options":sorted(options)})
  else:missing.append(row)
 report={"season":2016,"source":URL,"source_published":"2015-11-12",
  "rankings_extracted":351,"mapped":mapped,"unresolved":missing,"ambiguous":ambiguous,
  "ready_for_import":not missing and not ambiguous}
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(report,indent=2)+"\\n")
 print("2015-16:",len(rows),"rankings;",len(mapped),"mapped;",len(missing),"unresolved;",len(ambiguous),"ambiguous")
 print("Unresolved:",[x["team"] for x in missing])
 print("Ambiguous:",[x["team"] for x in ambiguous])
 print("Publication unchanged; this workflow only creates a mapping audit.")
if __name__=="__main__":main()
