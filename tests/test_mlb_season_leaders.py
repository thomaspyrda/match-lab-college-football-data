import unittest
from build_mlb_season_leaders import normalize

class MLBSeasonLeadersTests(unittest.TestCase):
    def payload(self, stats, **kwargs):
        return {'stats':[{'group':{'displayName':'pitching'},'totalSplits':1,'splits':[
            dict(season='2026',player={'id':1,'fullName':'Player'},stat=stats,
                 team={'name':'Team'},**kwargs)]}]}

    def test_innings_are_outs_and_missing_rates_are_null(self):
        row=normalize(self.payload({'inningsPitched':'12.2','era':'-.--'}),'pitching',2026)[0]
        self.assertEqual(row['stats']['outs'],38)
        self.assertEqual(row['stats']['inningsPitched'],'12.2')
        self.assertIsNone(row['stats']['era'])

    def test_traded_player_total_is_one_row(self):
        rows=normalize(self.payload({'inningsPitched':'10.0'},numTeams=2),'pitching',2026)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['team'],'Multiple teams')

    def test_incomplete_and_duplicate_responses_fail(self):
        payload=self.payload({'inningsPitched':'10.0'})
        payload['stats'][0]['totalSplits']=2
        with self.assertRaises(ValueError): normalize(payload,'pitching',2026)
        payload['stats'][0]['splits']*=2
        with self.assertRaises(ValueError): normalize(payload,'pitching',2026)

if __name__=='__main__': unittest.main()
