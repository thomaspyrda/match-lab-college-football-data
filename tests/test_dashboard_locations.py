import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import refresh_nba_dashboard as nba
import refresh_cbb_dashboard as cbb
class LocationRecords(unittest.TestCase):
 def fixture(self):
  return [{'date':f'2026-10-{day:02d}T00:00:00Z','observed_complete_at':'2026-10-29T00:00:00Z','home':'a' if day<=6 else 'b','neutral':day==8,'teams':{'a':{'points':80},'b':{'points':70}},'market':{'observed_at':'2026-10-29T00:00:00Z','home_spread':-5,'total':140}} for day in range(1,9)]
 def test_nba_all_games_grouped_by_actual_location(self):
  with patch.object(nba,'verified_closing_market',side_effect=lambda g:g['market']):r=nba.location_market_records(self.fixture(),'a',datetime(2026,10,30,tzinfo=timezone.utc))
  self.assertEqual(r['Home']['games'],6);self.assertEqual(r['Home']['wins'],6);self.assertEqual(r['Home']['ppg'],80);self.assertEqual(r['Away']['games'],1);self.assertEqual(r['Neutral']['games'],1)
 def test_cbb_home_road_excludes_neutral(self):
  with patch.object(cbb,'derived_metrics',return_value={}):p=cbb.profile('a',self.fixture(),datetime(2026,10,30,tzinfo=timezone.utc))
  self.assertEqual(p['location_markets']['Home']['games'],6);self.assertEqual(p['location_markets']['Away']['games'],1);self.assertEqual(p['location_markets']['Neutral']['games'],1);self.assertEqual(p['location_markets']['Home']['ats']['wins'],6);self.assertEqual(p['location_markets']['Home']['ppg'],80)
if __name__=='__main__':unittest.main()
