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
   if len(cells)<3 or not re.fullmatch(r"\d{1,3}",cells[0]):continue
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
 # Historical TeamRankings abbreviations: explicitly expanded, never fuzzy-matched.
 historical_names={
 "GA Tech":"Georgia Tech","Central Mich":"Central Michigan","LA Lafayette":"Louisiana","LA Tech":"Louisiana Tech",
 "Miss State":"Mississippi State","St Josephs":"Saint Joseph's","Coastal Car":"Coastal Carolina",
 "St Bonavent":"St. Bonaventure","VA Tech":"Virginia Tech","Wm & Mary":"William & Mary",
 "Middle Tenn":"Middle Tennessee","Northeastrn":"Northeastern","N Florida":"North Florida",
 "Loyola-Chi":"Loyola Chicago","St Marys":"Saint Mary's","Wash State":"Washington State",
 "N Mex State":"New Mexico State","TX Christian":"TCU","WI-Grn Bay":"Green Bay",
 "Lg Beach St":"Long Beach State","James Mad":"James Madison","TX El Paso":"UTEP",
 "New Jersey Tech":"NJIT","Geo Mason":"George Mason","NW State":"Northwestern State",
 "N Hampshire":"New Hampshire","Sam Hous St":"Sam Houston","E Washingtn":"Eastern Washington",
 "Boston Col":"Boston College","Bowling Grn":"Bowling Green","E Carolina":"East Carolina",
 "W Kentucky":"Western Kentucky","LA Monroe":"Louisiana Monroe","NC-Wilmington":"UNC Wilmington",
 "TX A&M-CC":"Texas A&M-Corpus Christi","WI-Milwkee":"Milwaukee","LIU-Brooklyn":"LIU Brooklyn",
 "U Penn":"Pennsylvania","S Florida":"South Florida","Mt St Marys":"Mount St. Mary's",
 "Rob Morris":"Robert Morris","Central FL":"UCF","AR Lit Rock":"Little Rock",
 "TX-Arlington":"UT Arlington","South Carolina Upstate":"USC Upstate","St Fran (NY)":"St. Francis Brooklyn",
 "TX Southern":"Texas Southern","Fla Gulf Cst":"Florida Gulf Coast","TN Martin":"UT Martin",
 "NC-Grnsboro":"UNC Greensboro","S Alabama":"South Alabama","IPFW":"Fort Wayne",
 "Fla Atlantic":"Florida Atlantic","VA Military":"VMI","CS Fullerton":"Cal State Fullerton",
 "Col Charlestn":"College of Charleston","CS Bakersfd":"Cal State Bakersfield",
 "TN State":"Tennessee State","Sacred Hrt":"Sacred Heart","NC-Asheville":"UNC Asheville",
 "St Peters":"Saint Peter's","Gard-Webb":"Gardner-Webb","TX-San Ant":"UTSA",
 "St Fran (PA)":"Saint Francis Pennsylvania","Sac State":"Sacramento State",
 "S Mississippi":"Southern Miss","Florida Intl":"FIU","Northern Kentucky":"Northern Kentucky",
 "Maryland ES":"Maryland Eastern Shore","Utah Val St":"Utah Valley","Houston Bap":"Houston Christian",
 "Massachusetts Lowell":"UMass Lowell","Alab A&M":"Alabama A&M","SIU Edward":"SIU Edwardsville",
 "F Dickinson":"Fairleigh Dickinson","Beth-Cook":"Bethune-Cookman",
 "Jksnville St":"Jacksonville State","Car State":"South Carolina State",
 "TX-Pan Am":"UT Rio Grande Valley","Central Conn":"Central Connecticut",
 "San Jose St":"San Jose State","Ark Pine Bl":"Arkansas-Pine Bluff",
 "Maryland BC":"UMBC","Central Ark":"Central Arkansas","Miss Val St":"Mississippi Valley State",
 "N Arizona":"Northern Arizona","Alab State":"Alabama State","Nicholls St":"Nicholls",
 "Youngs St":"Youngstown State","St Francis NY":"St. Francis Brooklyn"
 }
 for historical,canonical in historical_names.items():
  possibilities=aliases.get(norm(canonical),set())
  if len(possibilities)==1:aliases[norm(historical)].update(possibilities)
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
 args.output.write_text(json.dumps(report,indent=2)+"\n")
 print("2015-16:",len(rows),"rankings;",len(mapped),"mapped;",len(missing),"unresolved;",len(ambiguous),"ambiguous")
 print("Unresolved:",[x["team"] for x in missing])
 print("Ambiguous:",[x["team"] for x in ambiguous])
 print("Publication unchanged; this workflow only creates a mapping audit.")
if __name__=="__main__":main()
