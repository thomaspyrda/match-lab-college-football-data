"""Diagnose historical 2017-18 CBB Match Lab coverage without modifying data."""
import json
from pathlib import Path
from collections import Counter,defaultdict
root=Path(__file__).resolve().parent
teams=json.loads((root/"data/sports/team-registry.json").read_text())["teams"]
schools=[t for t in teams if t.get("sport")=="cbb"]
stats=Counter();samples=defaultdict(list)
for team in schools:
 slug=team["slug"];tp=root/f"data/cbb/teams/{slug}.json";mp=root/f"data/cbb/markets/{slug}.json"
 if not tp.exists():stats["missing_team_file"]+=1;continue
 data=json.loads(tp.read_text());season=data.get("seasons",{}).get("2018")
 if not season:stats["missing_2018_team_season"]+=1;continue
 stats["team_2018_season"]+=1
 games=[g for ph in season.get("phases",{}).values() for g in ph.get("games",[])]
 stats["team_game_rows"]+=len(games)
 finals=[g for g in games if str(g.get("status","")).lower() in ("final","completed")]
 stats["team_final_rows"]+=len(finals)
 if not finals and len(samples["no_finals"])<5:samples["no_finals"].append(slug)
 if not mp.exists():stats["missing_market_file"]+=1;continue
 market=json.loads(mp.read_text()).get("games",{}).get("2018",{})
 stats["market_2018_rows"]+=len(market)
 if not market and len(samples["no_market"])<5:samples["no_market"].append(slug)
eligible=json.loads((root/"cbb/match-lab/data/verified-historical.json").read_text())["games"]
stats["2018_verified_games"]=sum(g["season"]==2018 for g in eligible)
print("2017-18 COVERAGE:",dict(stats))
print("SAMPLES:",dict(samples))
print("Reason: exact 2018 eligibility needs both team final records and pre-tip verified historical markets; no synthetic games permitted.")
