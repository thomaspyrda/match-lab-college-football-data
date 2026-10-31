"""Import dated Bart Torvik rating snapshots via the public basketball-data DuckDB catalog.

Use only source rows observed before the game. A season's earliest snapshot is
preseason only when all teams show zero games; otherwise it is not preseason.
Requires source redistribution rights before public publishing.
"""
import argparse,json,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CATALOG="https://basketball-data.billmill.org/ncaam/ncaam.duckdb"
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--season",type=int,required=True)
 p.add_argument("--catalog",default=CATALOG)
 p.add_argument("--output",type=Path)
 a=p.parse_args()
 if not 2016<=a.season<=2027:raise ValueError("Season outside supported range")
 import duckdb
 con=duckdb.connect()
 con.execute("INSTALL httpfs; LOAD httpfs")
 con.execute(f"ATTACH '{a.catalog}' AS archive (READ_ONLY)")
 # Join exact ESPN team ids through the catalog, avoiding fuzzy school matching.
 rows=con.execute("""
 SELECT CAST(t.team_id AS VARCHAR), CAST(d.date AS VARCHAR), d.barthag,
        d.adj_oe, d.adj_de, d.wins, d.losses, t.torvik_team
 FROM archive.torvik_ratings_daily d
 JOIN archive.team_seasons t ON t.season=d.season AND t.torvik_team=d.team
 WHERE d.season=?
 ORDER BY t.team_id,d.date
 """,[a.season]).fetchall()
 by_team={}
 for tid,day,barthag,oe,de,wins,losses,name in rows:
  values={"date":day,"source":"Bart Torvik as-published daily archive","team":name}
  for key,v in (("barthag",barthag),("off_eff",oe),("def_eff",de),("wins",wins),("losses",losses)):
   if v is not None:values[key]=float(v) if key not in ("wins","losses") else int(v)
  by_team.setdefault(tid,[]).append(values)
 # Infer rank only within a complete dated Division I snapshot.
 day_rows={}
 for tid,items in by_team.items():
  for row in items:day_rows.setdefault(row["date"],[]).append((tid,row))
 preseason={}
 for day,entries in day_rows.items():
  if len(entries)<300:continue
  ranked=sorted(((tid,r) for tid,r in entries if r.get("barthag") is not None),key=lambda x:-x[1]["barthag"])
  if len(ranked)<300:continue
  for n,(tid,r) in enumerate(ranked,1):r["strength_rank"]=n
  # Only snapshot dates before the season opener can count as preseason.
  if all(r.get("wins")==0 and r.get("losses")==0 for _,r in entries):
   for n,(tid,r) in enumerate(ranked,1):
    existing=preseason.get(tid)
    if existing is None or day<existing["as_of"]:
     preseason[tid]={"rank":n,"as_of":day,"source_url":CATALOG}
 # Attach a preseason rank as distinct metadata; do not confuse Torvik with KenPom.
 for tid,items in by_team.items():
  if tid in preseason:
   for row in items:row["preseason_rank"]=preseason[tid]["rank"]
 out=a.output or ROOT/f"cbb/match-lab/data/torvik-daily-{a.season}.json"
 out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({"season":a.season,"source_url":CATALOG,"teams":by_team,"preseason":preseason},separators=(",",":"))+"\n")
 print(f"{a.season}: {len(by_team)} teams, {sum(len(v) for v in by_team.values())} dated rows, {len(preseason)} preseason ranks")
if __name__=="__main__":main()
