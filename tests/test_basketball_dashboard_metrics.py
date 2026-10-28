import copy
import unittest
from datetime import datetime, timezone
from basketball_dashboard_metrics import derived_metrics
import refresh_nba_dashboard as nba
import refresh_cbb_dashboard as cbb


class BasketballMetricsTests(unittest.TestCase):
    def game(self):
        own={'points':100,'fgm':35,'fga':80,'tpm':10,'tpa':32,'ftm':20,'fta':25,'oreb':10,'dreb':30,'reb':40,'ast':25,'tov':10,'stl':8,'blk':4,'paint_points':42}
        opp={**own,'points':90,'tpa':20,'reb':60,'tov':15,'paint_points':30}
        return {'id':'one','date':'2026-10-21T01:00:00Z','observed_complete_at':'2026-10-21T05:00:00Z','teams':{'1':own,'2':opp},'home':'1','players':{}}

    def test_rates_use_attempts_rebound_share_and_per_game_margin(self):
        m=derived_metrics([self.game()],'1')
        self.assertEqual(m['three_attempt_rate'],40)
        self.assertEqual(m['opp_three_attempt_rate'],25)
        self.assertEqual(m['total_rebound_rate'],40)
        self.assertEqual(m['opp_total_rebound_rate'],60)
        self.assertEqual(m['opp_rebounds_per_game'],60)
        self.assertEqual(m['turnover_margin'],5)
        self.assertEqual(m['points_in_paint'],42)
        self.assertEqual(m['opp_points_in_paint'],30)

    def test_missing_paint_does_not_publish_a_partial_season_average(self):
        one=self.game();two=copy.deepcopy(one);two['id']='two';del two['teams']['2']['paint_points']
        m=derived_metrics([one,two],'1')
        self.assertIsNone(m['opp_points_in_paint'])
        self.assertEqual(m['points_in_paint'],42)

    def test_missing_rebounds_and_zero_attempts_stay_unavailable(self):
        game=self.game();del game['teams']['2']['reb'];game['teams']['1']['fga']=0
        m=derived_metrics([game],'1')
        self.assertIsNone(m['total_rebound_rate'])
        self.assertIsNone(m['opp_rebounds_per_game'])
        self.assertIsNone(m['three_attempt_rate'])
        self.assertTrue(all(v is None for v in derived_metrics([],'1').values()))

    def test_nba_and_cbb_use_only_the_profile_cutoff_sample(self):
        one=self.game();future=copy.deepcopy(one);future['observed_complete_at']='2026-10-23T05:00:00Z';future['teams']['1']['paint_points']=100
        for module in [nba,cbb]:
            profile=module.profile('1',[one,future],datetime(2026,10,22,tzinfo=timezone.utc))
            self.assertEqual(profile['metrics']['points_in_paint'],42)
            self.assertEqual(profile['metrics']['turnover_margin'],5)

    def test_cbb_box_collects_actual_paint_field_without_imputing_it(self):
        row={'statistics':[{'name':'pointsInPaint','displayValue':'38'}]}
        self.assertEqual(cbb.team_box(row,80)['paint_points'],38)
        self.assertIsNone(cbb.team_box({'statistics':[]},80)['paint_points'])


if __name__=='__main__':unittest.main()
