"""Import an explicitly sourced, dated Torvik preseason full-field ranking export.

Input CSV columns: season,team,rank,as_of,source_url.
Rows must be pre-season, distinct, and map unambiguously to an ESPN team
registry entry. No fuzzy name matching or season-end rating substitution.
This importer is intentionally file-based: use only legitimately obtained data
with publication/redistribution permission.
"""
import argparse,csv,json,re
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parent
def norm(s):return re.sub(r"[^a-z0-9]","",str(s).lower())
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--csv",type=Path,required=True)
 p.add_argument("--output",type=Path,default=ROOT/"cbb/match-lab/data/preseason-ranks.json")
 p.add_argument("--min-coverage",type=int,default=300)
 args=p.parse_args()
 teams=json.loads((ROOT/"data/sports/team-registry.json").read_text())["teams"]
 aliases={}
 for t in teams:
  if t.get("sport")!="cbb":continue
  for name in [t.get("name"),t.get("short_name"),*(t.get("aliases") or [])]:
   key=norm(name)
   if key:aliases.setdefault(key,set()).add(t["slug"])
 result={};seen={}
 with args.csv.open(newline="") as stream:
  for row in csv.DictReader(stream):
   season=int(row["season"]);rank=int(row["rank"]);as_of=date.fromisoformat(row["as_of"])
   if not 2016<=season<=2027 or not 1<=rank<=400 or as_of.year not in (season-1,season):
    raise ValueError("Invalid preseason season/rank/date")
   # Require an observed date before November 1 of the season's starting year.
   if as_of>=date(season-1,11,1):raise ValueError("Not a preseason snapshot: "+str(row))
   url=row["source_url"]
   if not url.startswith("https://barttorvik.com/"):raise ValueError("Unexpected source URL")
   options=aliases.get(norm(row["team"]),set())
   if len(options)!=1:raise ValueError("Ambiguous or unrecognized team: "+row["team"])
   slug=next(iter(options));year=str(season)
   if slug in result.setdefault(year,{}):raise ValueError("Duplicate school")
   if rank in seen.setdefault(year,set()):raise ValueError("Duplicate rank")
   seen[year].add(rank)
   result[year][slug]={"rank":rank,"as_of":as_of.isoformat(),"source_url":url}
 for year,teams in result.items():
  if len(teams)<args.min_coverage:raise ValueError(f"{year}: only {len(teams)} validated ranks, expected full-field coverage")
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps({"source":"Bart Torvik archived preseason T-Rank","seasons":result},separators=(",",":"))+"\n")
 print("Validated preseason ranks:",{y:len(t) for y,t in result.items()})
if __name__=="__main__":main()
