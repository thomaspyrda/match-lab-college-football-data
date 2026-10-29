import copy,unittest
from build_mlb_team_rankings import build
from finalize_mlb_season import outcomes
import json
from pathlib import Path
class FinalSeason(unittest.TestCase):
 def test_no_world_series_finish_does_not_publish_missed_playoffs(self):
  self.assertIsNone(outcomes({'dates':[]}))
 def test_offseason_defaults_to_previous_season_until_games_start(self):
  root=Path(__file__).resolve().parents[1]
  snapshot=json.loads((root/'data/mlb/season-snapshots.json').read_text())
  registry=json.loads((root/'data/sports/team-registry.json').read_text())
  old=max(snapshot['seasons'],key=int)
  snapshot['seasons']['2099']=copy.deepcopy(snapshot['seasons'][old])
  for t in snapshot['seasons']['2099'].values():t.update(games_played=0,wins=0,losses=0,ties=0)
  self.assertEqual(build(snapshot,registry)['default_season'],old)
