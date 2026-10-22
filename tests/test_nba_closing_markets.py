import unittest
from nba_closing_markets import closing_market,verified_closing_market
from stage_nba_team_backfill import build_manifest
from test_stage_nba_team_backfill import registry,game

class ClosingMarkets(unittest.TestCase):
    def quote(self,home='-10',away='+10',over='o210',under='u210'):
        return {'pickcenter':[{'provider':{'name':'DraftKings'},'pointSpread':{'home':{'close':{'line':home},'open':{'line':'-4'}},'away':{'close':{'line':away}}},'total':{'over':{'close':{'line':over}},'under':{'close':{'line':under}}}}]}
    def test_closing_not_opening_and_both_sides_settle_push(self):
        g=game();g['closing_market']=closing_market(self.quote(),'999',g['observed_complete_at'])
        self.assertEqual(g['closing_market']['home_spread'],-10)
        rows=build_manifest(registry(),{'games':[g]})['teams']
        self.assertEqual(rows['team-1'][0]['ats_result'],'P')
        self.assertEqual(rows['team-2'][0]['ats_result'],'P')
        self.assertEqual(rows['team-1'][0]['ou_result'],'Push')
    def test_signed_spreads_and_total_results(self):
        g=game();g['closing_market']=closing_market(self.quote('-9.5','+9.5','o208.5','u208.5'),'999',g['observed_complete_at'])
        r=build_manifest(registry(),{'games':[g]})['teams']
        self.assertEqual(r['team-1'][0]['ats_result'],'W');self.assertEqual(r['team-2'][0]['ats_result'],'L')
        self.assertEqual(r['team-2'][0]['ou_result'],'Over')
    def test_opening_and_legacy_not_used_as_closing(self):
        self.assertIsNone(closing_market({'pickcenter':[{'spread':10,'overUnder':210,'pointSpread':{'home':{'open':{'line':'-10'}}}}]},'999','now'))
        g=game();g['market']={'home_spread':-10,'total':210};self.assertIsNone(verified_closing_market(g))
    def test_conflicts_and_nonfinite_lines_not_published(self):
        self.assertIsNone(closing_market(self.quote('-10','+5','o210','u220'),'999','now'))
        self.assertIsNone(closing_market(self.quote('nan','inf','oNaN','uInfinity'),'999','now'))
    def test_game_source_must_match(self):
        g=game();g['closing_market']=closing_market(self.quote(),'another-game','now');self.assertIsNone(verified_closing_market(g))
