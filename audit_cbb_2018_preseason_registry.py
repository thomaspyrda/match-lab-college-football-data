"""Audit original Torvik 2017-18 preseason ranking capture against ESPN team registry.
This is a candidate audit only. It never publishes or substitutes in-season rankings.
"""
import argparse,csv,json,re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def norm(value):
 words=re.findall(r"[a-z0-9]+",str(value or "").lower())
 # Equivalent spelling only; do not infer unrelated schools.
 return "".join("state" if word in ("st","state") else word for word in words)

# Explicit historical school abbreviations; avoid fuzzy assignments.
OVERRIDES={"michigan st.":"Michigan State","wichita st.":"Wichita State",
"ohio st.":"Ohio State","penn st.":"Penn State","florida st.":"Florida State",
"iowa st.":"Iowa State","kansas st.":"Kansas State","oklahoma st.":"Oklahoma State",
"arizona st.":"Arizona State","colorado st.":"Colorado State",
"mississippi st.":"Mississippi State","boise st.":"Boise State",
"utah st.":"Utah State","oregon st.":"Oregon State",
"san diego st.":"San Diego State","fresno st.":"Fresno State",
"new mexico st.":"New Mexico State","ball st.":"Ball State",
"kent st.":"Kent State","cleveland st.":"Cleveland State",
"wright st.":"Wright State","weber st.":"Weber State",
"murray st.":"Murray State","morehead st.":"Morehead State",
"tennessee st.":"Tennessee State","jacksonville st.":"Jacksonville State",
"missouri st.":"Missouri State","indiana st.":"Indiana State",
"illinois st.":"Illinois State","portland st.":"Portland State",
"northwestern st.":"Northwestern State","sam houston st.":"Sam Houston",
"youngstown st.":"Youngstown State","appalachian st.":"App State",
"long beach st.":"Long Beach State","sacramento st.":"Sacramento State"}
HISTORICAL_SLUGS={
  "miami fl": "miami-hurricanes",
  "mississippi": "ole-miss-rebels",
  "college of charleston": "charleston-cougars",
  "connecticut": "uconn-huskies",
  "florida gulf coast": "florida-gulf-coast-eagles",
  "albany": "ualbany-great-danes",
  "middle tennessee": "middle-tennessee-blue-raiders",
  "louisiana lafayette": "louisiana-ragin-cajuns",
  "massachusetts": "massachusetts-minutemen",
  "pittsburgh": "pittsburgh-panthers",
  "uc santa barbara": "uc-santa-barbara-gauchos",
  "jacksonville st.": "jacksonville-state-gamecocks",
  "illinois chicago": "uic-flames",
  "cal st. bakersfield": "cal-state-bakersfield-roadrunners",
  "florida atlantic": "florida-atlantic-owls",
  "detroit": "detroit-mercy-titans",
  "western kentucky": "western-kentucky-hilltoppers",
  "fort wayne": "purdue-fort-wayne-mastodons",
  "george washington": "george-washington-revolutionaries",
  "boston university": "boston-university-terriers",
  "fairleigh dickinson": "fairleigh-dickinson-knights",
  "seattle": "seattle-u-redhawks",
  "charleston southern": "charleston-southern-buccaneers",
  "nicholls st.": "nicholls-colonels",
  "mcneese st.": "mcneese-cowboys",
  "texas a&m corpus chris": "texas-am-corpus-christi-islanders",
  "central michigan": "central-michigan-chippewas",
  "new orleans": "new-orleans-privateers",
  "cal st. fullerton": "cal-state-fullerton-titans",
  "tennessee martin": "ut-martin-skyhawks",
  "maryland eastern shore": "maryland-eastern-shore-hawks",
  "siu edwardsville": "siu-edwardsville-cougars",
  "southeast missouri st.": "southeast-missouri-state-redhawks",
  "grambling st.": "grambling-tigers",
  "central connecticut": "central-connecticut-blue-devils",
  "south carolina st.": "south-carolina-state-bulldogs",
  "cal st. northridge": "cal-state-northridge-matadors",
  "nebraska omaha": "omaha-mavericks",
  "uc upstate": "usc-upstate-spartans"
}
ADDITIONAL_HISTORICAL_SLUGS = {
  "southeastern louisiana": "se-louisiana-lions",
  "louisiana monroe": "louisiana-monroe-warhawks",
  "houston baptist": "houston-christian-huskies",
  "usc upstate": "south-carolina-upstate-spartans",
  "umkc": "kansas-city-roos",
  "iupui": "iu-indianapolis-jaguars"
}
HISTORICAL_ONLY={
 'liu brooklyn':'historical:liu-brooklyn',
 'savannah st.':'historical:savannah-state',
 'hartford':'historical:hartford',
 'st. francis ny':'historical:st-francis-brooklyn',
 'st. francis pa':'historical:st-francis-pennsylvania'
}
# Preserve known schools that are missing or mislabeled in the current team registry.
# These retain historical identities; do not map them to an unrelated team.
MISSING_REGISTRY_HISTORICAL={
 "louisiana monroe":"historical:louisiana-monroe",
 "san jose st.":"historical:san-jose-state",
 "new orleans":"historical:new-orleans"
}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--csv",type=Path,required=True)
 p.add_argument("--output",type=Path,default=Path("cbb/match-lab/imports/preseason-review/2018-team-audit.json"))
 args=p.parse_args()
 registry=json.loads((ROOT/"data/sports/team-registry.json").read_text())["teams"]
 aliases=defaultdict(set)
 for t in registry:
  if t.get("sport")!="cbb":continue
  for key in [t.get("name"),t.get("short_name"),t.get("abbreviation"),*(t.get("aliases") or [])]:
   if norm(key):aliases[norm(key)].add(t["slug"])
 mapped=[];unresolved=[];ambiguous=[];historical_only=[];used=set();ranks=set()
 with args.csv.open(newline="") as handle:
  for row in csv.DictReader(handle):
   season=int(row["season"]);rank=int(row["rank"])
   if season!=2018 or not 1<=rank<=351 or rank in ranks:raise ValueError("Invalid or repeated historical rank")
   ranks.add(rank)
   original=row["team"];name=OVERRIDES.get(original.lower(),original)
   options=aliases.get(norm(original),set()) or aliases.get(norm(name),set())
   if not options and re.search(r"\bSt\.?$",name,re.I):
    options=aliases.get(norm(re.sub(r"\bSt\.?$","State",name,flags=re.I)),set())
   if not options and re.search(r"\bCal St\.?",name,re.I):
    options=aliases.get(norm(re.sub(r"\bCal St\.?","Cal State",name,flags=re.I)),set())
   # Historical spellings can disagree with ESPN's present-day short label.
   # Resolve only when exactly one registry school matches an approved variant.
   if not options:
    variants=[name.replace("Saint ","St ").replace("St. ","St "),
              name.replace("State","St"),name.replace("St.","St"),
              name.replace("University of ",""),name.replace("Cal St.","Cal State"),
              name.replace("North Carolina","NC"),name.replace("Southern","S"),
              name.replace("Western","W"),name.replace("Eastern","E"),
              name.replace("Northern","N")]
    candidates=set()
    for variant in variants:candidates.update(aliases.get(norm(variant),set()))
    options=candidates
   if not options and original.lower() in HISTORICAL_SLUGS:
    options={HISTORICAL_SLUGS[original.lower()]}
   options={slug for slug in options if slug in {t["slug"] for t in registry if t.get("sport")=="cbb"}}
   if not options and original.lower() in ADDITIONAL_HISTORICAL_SLUGS:
    options={ADDITIONAL_HISTORICAL_SLUGS[original.lower()]}
   options={slug for slug in options if slug in {t["slug"] for t in registry if t.get("sport")=="cbb"}}
   if not options and original.lower() in MISSING_REGISTRY_HISTORICAL:
    historical_only.append({"rank":rank,"team":original,"historical_id":MISSING_REGISTRY_HISTORICAL[original.lower()]})
    continue
   if len(options)!=1:
    if not options and original.lower() in HISTORICAL_ONLY:
     historical_only.append({'rank':rank,'team':original,'historical_id':HISTORICAL_ONLY[original.lower()]})
    else:
     (unresolved if not options else ambiguous).append({'rank':rank,'team':original,'candidates':sorted(options)})
    continue
   slug=next(iter(options))
   if slug in used:ambiguous.append({"rank":rank,"team":original,"reason":"duplicate registry school","slug":slug});continue
   used.add(slug);mapped.append({"rank":rank,"team":original,"slug":slug})
 if ranks!=set(range(1,352)):raise ValueError("Historical ranks are not sequential 1–351")
 report={"season":2018,"source":"Torvik original preseason archived page candidate","mapped_count":len(mapped),
         "unresolved":unresolved,"ambiguous":ambiguous,"historical_only":historical_only,"mapped":mapped,
         "publication_allowed":False,"provenance_verified":False}
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(report,indent=2)+"\n")
 print("Mapped:",len(mapped),"historical-only:",len(historical_only),"unresolved:",len(unresolved),"ambiguous:",len(ambiguous))
 print("Unresolved schools:",[x["team"] for x in unresolved])
 print("Ambiguous:",ambiguous)
if __name__=="__main__":main()
