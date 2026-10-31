"""Read-only CBB preseason ranking coverage audit for 2015-present."""
import json
from pathlib import Path
from collections import Counter
base=Path(__file__).resolve().parent
r=json.loads((base/"cbb/match-lab/data/preseason-ranks.json").read_text())
seasons=r.get("seasons",{})
archive=json.loads((base/"cbb/match-lab/data/verified-historical.json").read_text())
games=archive.get("games",[])
for year in range(2015,2027):
 ranks=seasons.get(str(year),{})
 eligible=[g for g in games if g.get("season")==year]
 both=sum(g.get("away",{}).get("profile",{}).get("preseason_rank") is not None and g.get("home",{}).get("profile",{}).get("preseason_rank") is not None for g in eligible)
 print(f"season={year} imported_preseason_teams={len(ranks)} verified_games={len(eligible)} games_both_ranked={both}")
