import json, tempfile, unittest, urllib.error, sys
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import sync_cbb_market_archives as cbb_markets
from scripts.verify_sport_dataset_contract import verify_nba_schedule_results
class Repairs(unittest.TestCase):
 def test_optional_odds_failure_preserves_captures(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'teams').mkdir();ledger=p/'ledger.json';ledger.write_text(json.dumps({'season':2027,'games':{'old':{'id':'old'}}}))
   with patch.object(cbb_markets,'LEDGER',ledger),patch.object(cbb_markets,'TEAMS',p/'teams'),patch.object(cbb_markets,'MARKETS',p/'markets'),patch.dict('os.environ',{'CBBD_API_KEY':'test'}),patch.object(cbb_markets,'capture_event',return_value={'id':'new','home_spread':-2,'total':150}),patch.object(cbb_markets,'fetch_cbbd_lines',side_effect=urllib.error.HTTPError('https://example.invalid',429,'limited',{},None)):
    d=cbb_markets.update(now=datetime(2026,11,10,tzinfo=timezone.utc),fetch=lambda _: {'events':[{}]})
   self.assertEqual(set(d['games']),{'old','new'});self.assertEqual(d['provider_status']['cbbd_archive']['http_status'],429);self.assertEqual(json.loads(ledger.read_text()),d)
 def test_nba_requires_two_consistent_final_results(self):
  d={'freshness':{'expected_previous_day_games':['one']}};a={'game_id':'one','result':'W','score_for':110,'score_against':100};b={'game_id':'one','result':'L','score_for':100,'score_against':110};s={'teams':{'a':{'games':[a]},'b':{'games':[b]}}};self.assertEqual(verify_nba_schedule_results(s,d),1)
  b['score_against']=111
  with self.assertRaises(ValueError):verify_nba_schedule_results(s,d)
if __name__=='__main__':unittest.main()
