"""Merge six verified season-opening rankings from archived dated Torvik snapshots.

Fails closed: only preseason observations from the upstream importer; never use
post-tip or season-end rankings and never overwrite established seasons.
"""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
YEARS=range(2021,2027)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--min-teams",type=int,default=300)
 a=ap.parse_args()
 registry=json.loads((ROOT/"data/sports/team-registry.json").read_text())["teams"]
 id_to_slug={str(t["espn_id"]):t["slug"] for t in registry if t.get("sport")=="cbb" and t.get("espn_id")}
 path=ROOT/"cbb/match-lab/data/preseason-ranks.json"
 original=json.loads(path.read_text())
 additions={}
 for year in YEARS:
  source=ROOT/f"cbb/match-lab/data/torvik-daily-{year}.json"
  payload=json.loads(source.read_text())
  if payload.get("season")!=year:raise ValueError(f"{year}: wrong source season")
  entries=payload.get("preseason",{})
  if len(entries)<a.min_teams:raise ValueError(f"{year}: only {len(entries)} genuine preseason ranks; expected >= {a.min_teams}")
  rank_nums=[int(row["rank"]) for row in entries.values()]
  if len(set(rank_nums))!=len(entries):raise ValueError(f"{year}: duplicate preseason rank numbers")
  mapped={};unknown=[]
  for team_id,entry in entries.items():
   slug=id_to_slug.get(str(team_id))
   if not slug:
    unknown.append({"espn_id":str(team_id),"rank":int(entry["rank"])})
    continue
   if slug in mapped:raise ValueError(f"{year}: duplicate canonical identity {slug}")
   mapped[slug]={"rank":int(entry["rank"]),"source":"Bart Torvik dated preseason snapshot"}
  if len(mapped)<a.min_teams:raise ValueError(f"{year}: insufficient valid mapped team identities ({len(mapped)})")
  # Do not lose unmatched historical identities; report them separately.
  additions[str(year)]=(mapped,unknown)
  print(f"{year-1}-{str(year)[-2:]}: {len(entries)} preseason rankings; {len(mapped)} registry teams; {len(unknown)} historical/unmatched ESPN IDs")
 # All seasons must validate before mutating destination.
 for year,(mapped,unmatched) in additions.items():
  existing=original.setdefault("seasons",{}).get(year)
  if existing and existing!=mapped:raise ValueError(f"{year} already contains conflicting rankings; refusing overwrite")
  original["seasons"][year]=mapped
  original.setdefault("historical_only",{})[year]=unmatched
  original.setdefault("source_notes",{})[year]={"source":"Dated Bart Torvik preseason power ratings","scope":"ranking derived only from all-zero-game season-opening dated observations"}
 path.write_text(json.dumps(original,indent=2)+"\n")
 print("Validated six preseason seasons and saved rankings without touching 2016-2020.")
if __name__=="__main__":main()
