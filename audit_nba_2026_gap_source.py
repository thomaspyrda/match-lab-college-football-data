#!/usr/bin/env python3
"""Audit candidate full-season 2025-26 NBA odds against verified team game records.
This is an evaluation, not an endorsement of the source or permission to publish.
"""
import csv, io, json, urllib.request, re
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parent
URL="https://huggingface.co/datasets/minmaxxxer/nba-closing-lines-ats-2025-26/resolve/main/nba_2025_26_closing_lines_ats.csv"
DATA=ROOT/"nba/teams/data"
ALIASES={"Los Angeles Clippers":"LA Clippers","LA Clippers":"LA Clippers","New Orleans Pelicans":"New Orleans Pelicans"}
def norm(n):return re.sub(r'[^a-z0-9]', '', ALIASES.get(n,n).lower())
def main():
  req=urllib.request.Request(URL,headers={"User-Agent":"BetWise NBA historical backfill audit"})
  with urllib.request.urlopen(req,timeout=70) as response:
    records=list(csv.DictReader(io.StringIO(response.read().decode("utf-8-sig"))))
  rows={}
  for r in records:
    if str(r.get("season_type","")).lower() not in ("regular","regular season"):continue
    k=(r["date_et"][:10],norm(r["home_team"]),norm(r["away_team"]))
    rows.setdefault(k,[]).append(r)
  summary=Counter();disagreements=[];samples=[]
  for path in sorted(DATA.glob("*-season-details.json")):
    doc=json.loads(path.read_text())
    for game in doc.get("seasons",{}).get("2026",{}).get("games",[]):
      if game.get("spread") is not None and game.get("total") is not None:continue
      summary["missing_before"]+=1
      # Find by date, opponent, home/away, and exact score, not by date alone.
      possible=[r for (day,home,away),batch in rows.items() if day==game["date"]
         and (away if game["location"]=="Home" else home)==norm(game["opponent_name"])
         for r in batch]
      # Record rejection reasons; candidate dataset may have unreliable game data.
      score_matches=[r for r in possible if
       int(float(r["home_score"]))==(game["score_for"] if game["location"]=="Home" else game["score_against"])
       and int(float(r["away_score"]))==(game["score_against"] if game["location"]=="Home" else game["score_for"])]
      if len(score_matches)!=1:
        summary["unmatched_or_score_mismatch"]+=1
        if possible and len(disagreements)<20:disagreements.append({"game_id":game["game_id"],"date":game["date"],"possible":len(possible),"scores_match":len(score_matches)})
        continue
      r=score_matches[0]
      try:
        spread=float(r["close_spread_home"]);total=float(r["close_total"])
      except (KeyError,TypeError,ValueError):
        summary["no_valid_market"]+=1
        continue
      summary["eligible"]+=1
      if len(samples)<5:samples.append({"game_id":game["game_id"],"date":game["date"],"home":r["home_team"],"away":r["away_team"],"spread_home":spread,"total":total})
  report={"candidate_rows":len(records),"source":URL,"coverage":dict(summary),"disagreement_samples":disagreements,"matched_samples":samples,"publication": "NOT PERFORMED"}
  print(json.dumps(report,indent=2))
  (ROOT/"nba/teams/data/2026-gap-source-audit.json").write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__":main()
