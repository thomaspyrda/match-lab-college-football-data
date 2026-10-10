#!/usr/bin/env python3
"""Collect 2015–2025 MLB managerial tenures from the Lahman historical CSVs.
Current 2026 and hitting/pitching coaches remain pending independent verification.
"""
import csv,io,json,urllib.request,collections
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE="https://raw.githubusercontent.com/corbtastik/lahman-baseball-db/main/"
def fetch(name):
 req=urllib.request.Request(BASE+name+".csv",headers={"User-Agent":"BetWiseResearch/1.0"})
 with urllib.request.urlopen(req,timeout=90) as r:return list(csv.DictReader(io.StringIO(r.read().decode("utf-8-sig"))))
def main():
 teams,managers,people=fetch("Teams"),fetch("Managers"),fetch("People")
 # Use the 2025 team code as the canonical reference, including historical identities.
 aliases={"ARI":"arizona-diamondbacks","ATL":"atlanta-braves","BAL":"baltimore-orioles","BOS":"boston-red-sox","CHC":"chicago-cubs","CHW":"chicago-white-sox","CIN":"cincinnati-reds","CLE":"cleveland-guardians","COL":"colorado-rockies","DET":"detroit-tigers","HOU":"houston-astros","KCR":"kansas-city-royals","LAA":"los-angeles-angels","LAD":"los-angeles-dodgers","MIA":"miami-marlins","MIL":"milwaukee-brewers","MIN":"minnesota-twins","NYM":"new-york-mets","NYY":"new-york-yankees","ATH":"athletics","PHI":"philadelphia-phillies","PIT":"pittsburgh-pirates","SDP":"san-diego-padres","SFG":"san-francisco-giants","SEA":"seattle-mariners","STL":"st-louis-cardinals","TBR":"tampa-bay-rays","TEX":"texas-rangers","TOR":"toronto-blue-jays","WSN":"washington-nationals"}
 franch={t["franchID"]:aliases[t["teamIDBR"]] for t in teams if t["yearID"]=="2025"}
 assert len(franch)==30
 seasonTeam={(int(t["yearID"]),t["teamID"]):franch.get(t["franchID"]) for t in teams}
 names={p["playerID"]:" ".join(filter(None,[p.get("nameFirst"),p.get("nameLast")])) for p in people}
 out={slug:{str(y):{"managers":[],"hitting_coaches":[],"pitching_coaches":[],"staff_status":"managers_only" if y<2026 else "not_loaded"} for y in range(2015,2027)} for slug in aliases.values()}
 for m in managers:
  y=int(m["yearID"])
  if not 2015<=y<=2025:continue
  slug=seasonTeam.get((y,m["teamID"]))
  if not slug:continue
  pid=m["playerID"]
  if not names.get(pid):raise ValueError(f"Manager name unresolved {pid}")
  out[slug][str(y)]["managers"].append({"name":names[pid],"player_id":pid,"order":int(m["inseason"]),"games":int(m["G"]),"wins":int(m["W"]),"losses":int(m["L"]),"source":BASE+"Managers.csv"})
 for slug,seasons in out.items():
  for y,record in seasons.items():
   record["managers"].sort(key=lambda x:x["order"])
   if int(y)<=2025 and not record["managers"]:raise ValueError(f"Missing {slug} manager for {y}")
   if len({p["player_id"] for p in record["managers"]})!=len(record["managers"]):raise ValueError(f"Duplicate manager: {slug} {y}")
 d={"schema_version":1,"source":"SABR Lahman Managers, Teams and People historical CSVs","as_of":datetime.now(timezone.utc).isoformat(),"coverage":"2015-2025 manager tenures; 2026 and assistant coaches pending","teams":out}
 path=ROOT/"data/mlb/coaching-history.json";path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(d,ensure_ascii=False,separators=(",",":"))+"\n")
 print("Manager seasons",sum(bool(v["managers"]) for ts in out.values() for v in ts.values()),"manager tenures",sum(len(v["managers"]) for ts in out.values() for v in ts.values()))
if __name__=="__main__":main()
