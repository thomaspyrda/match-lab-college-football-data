#!/usr/bin/env python3
"""Preserve published MLB market metadata across official-score rebuilds."""
import json,sys,pathlib,collections
old=pathlib.Path(sys.argv[1]);new=pathlib.Path(sys.argv[2])
published=json.loads(old.read_text());official=json.loads(new.read_text())
market_names={"team_runline_side","team_runline_result","runline_source","runline_source_url",
"runline_estimated","runline_side","runline_result","market_starter","market_opponent_starter",
"market_moneyline","market_runline_odds","market_ou_total","market_ou_result",
"market_over_odds","market_under_odds","market_source","market_ou_source"}
n=0;gids=set();skipped=0
for team,record in official["teams"].items():
 previous={str(g.get("game_id")):g for g in published.get("teams",{}).get(team,{}).get("games",[])}
 for game in record.get("games",[]):
  prior=previous.get(str(game.get("game_id")))
  if not prior:continue
  if prior.get("score")!=game.get("score") or prior.get("result")!=game.get("result"):
   skipped+=1;continue
  for key in market_names:
   if key in prior and prior[key] is not None:
    game[key]=prior[key];n+=1;gids.add(str(game.get("game_id")))
new.write_text(json.dumps(official,separators=(",",":"))+"\n")
print(json.dumps({"season":new.stem,"market_fields_restored":n,"games_restored":len(gids),"score_conflicts_skipped":skipped}))
