import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
import json
import backfill_cbb_team_archives as b

def payload(year=2016):
    return {'requestedSeason':{'year':year},'events':[{
        'id':'game-1','date':'2015-11-20T00:00Z','season':{'year':year},'seasonType':{'type':2},
        'competitions':[{'neutralSite':True,'status':{'type':{'completed':True}},'competitors':[
            {'id':'150','homeAway':'home','team':{'displayName':'Duke'},'score':{'value':80}},
            {'id':'153','homeAway':'away','team':{'displayName':'North Carolina'},'score':{'value':75}}]}]}]}

class CBBArchiveTests(unittest.TestCase):
    def test_team_perspective_and_phase_separation(self):
        with patch.object(b,'get',return_value=payload()):
            duke=b.schedule('150',2016,2)[0]
            unc=b.schedule('153',2016,2)[0]
            self.assertEqual((duke['result'],duke['points'],duke['location']),('W',80,'Neutral'))
            self.assertEqual((unc['result'],unc['points']),('L',75))
            self.assertEqual(b.schedule('150',2016,3),[])

    def test_duplicate_game_and_wrong_year_fail(self):
        data=payload();data['events']*=2
        with patch.object(b,'get',return_value=data):
            with self.assertRaises(ValueError):b.schedule('150',2016,2)
        with patch.object(b,'get',return_value=payload(2017)):
            with self.assertRaises(ValueError):b.schedule('150',2016,2)

    def test_backfill_resumes_missing_and_preserves_historical_seasons(self):
        with TemporaryDirectory() as tmp, patch.object(b,'OUT',Path(tmp)):
            team={'slug':'example','espn_id':'150'}
            saved={'team_id':'150','seasons':{'2016':{'sentinel':'validated'}}}
            (Path(tmp)/'example.json').write_text(json.dumps(saved))
            remaining=b.missing_team_seasons([team],[2016,2017,2027],2027)
            self.assertEqual(remaining,[('example',2017),('example',2027)])
            self.assertEqual(json.loads((Path(tmp)/'example.json').read_text()),saved)

    def test_backfill_refuses_changed_team_identity(self):
        with TemporaryDirectory() as tmp, patch.object(b,'OUT',Path(tmp)):
            (Path(tmp)/'example.json').write_text(json.dumps({'team_id':'999','seasons':{}}))
            with self.assertRaises(ValueError):
                b.missing_team_seasons([{'slug':'example','espn_id':'150'}],[2016],2027)

    def test_unavailable_is_not_a_zero_score(self):
        with patch.object(b,'get',return_value={'unavailable':True}):
            self.assertEqual(b.schedule('150',2016,2),[])
        data=payload();data['events'][0]['competitions'][0]['competitors'][0].pop('score')
        with patch.object(b,'get',return_value=data):
            with self.assertRaises(ValueError):b.schedule('150',2016,2)
if __name__=='__main__':unittest.main()
