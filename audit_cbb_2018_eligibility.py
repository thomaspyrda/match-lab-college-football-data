"""Read-only progressive eligibility audit for 2017-18 historical CBB games."""
import json
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime
R=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def dt(s):
 try:return datetime.fromisoformat(str(s).replace("Z","+00:00"))
 except (ValueError,TypeError):return None
def num(x):
 try:return float(x)
 except (ValueError,TypeError):return None
schools=[t for t in load(R/"data/sports/team-registry.json")["teams"] if t.get("sport")=="cbb"]
ids={str(t["espn_id"]):t for t in schools}
games=defaultdict(dict);markets=defaultdict(dict);counts=Counter();samples={}
for t in schools:
 slug=t["slug"];p=R/f"data/cbb/teams/{slug}.json";m=R/f"data/cbb/markets/{slug}.json"
 if p.exists():
  season=load(p).get("seasons",{}).get("2018",{})
  for phase in season.get("phases",{}).values():
   for g in phase.get("games",[]):
    if str(g.get("status","")).lower() not in ("final","completed"):continue
    if str(g.get("opponent_id")) not in ids or not g.get("id"):continue
    games[slug][str(g["id"])]=g
 if m.exists():
  for gid,line in load(m).get("games",{}).get("2018",{}).items():markets[str(gid)][slug]=line
for slug,rows in games.items():
 for gid,g in rows.items():
  if g.get("location")!="Home":continue
  counts["home_final"]+=1
  other=ids[str(g["opponent_id"])]["slug"]
  og=games.get(other,{}).get(gid)
  if og is None:counts["missing_opponent_game"]+=1;continue
  counts["both_archives"]+=1
  if og.get("location")!="Away" or str(og.get("opponent_id"))!=str(next(t["espn_id"] for t in schools if t["slug"]==slug)):
   counts["location_or_opponent_mismatch"]+=1;continue
  counts["paired_orientation"]+=1
  if num(g.get("points"))!=num(og.get("opponent_points")) or num(og.get("points"))!=num(g.get("opponent_points")):
   counts["scores_mismatch"]+=1;continue
  counts["paired_scores"]+=1
  a=markets.get(gid,{}).get(slug,{});b=markets.get(gid,{}).get(other,{})
  if not a or not b:counts["missing_pair_market"]+=1;continue
  counts["paired_markets"]+=1
  total=num(a.get("total"));spread=num(a.get("spread"));ot=num(b.get("total"));os=num(b.get("spread"))
  if None in (total,spread,ot,os):counts["market_missing_numbers"]+=1;continue
  counts["markets_numeric"]+=1
  if abs(total-ot)>.01 or abs(spread+os)>.01:counts["market_disagreement"]+=1;continue
  counts["market_agreement"]+=1
  tip=dt(g.get("date"));t1=dt(a.get("observed_at"));t2=dt(b.get("observed_at"))
  if not tip or not t1 or not t2:counts["missing_market_timestamps"]+=1;continue
  if t1>tip or t2>tip:counts["posttip_market_timestamp"]+=1;continue
  counts["pregame_market_timestamps"]+=1
  if a.get("line_type")!="provider historical line" or b.get("line_type")!="provider historical line":
   counts["line_type_rejected"]+=1;continue
  counts["line_type_passed"]+=1
print("2017-18 progressive eligibility:",dict(counts))
print("Interpretation: the first failed stage shows where rebuild excludes games; no verification rules changed.")
