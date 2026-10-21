import copy
import unittest
from datetime import datetime, timezone, timedelta
from nba_player_context import build_availability, normalize_injury, refresh_availability, player_values

NOW=datetime(2026,10,21,19,tzinfo=timezone.utc)


def injury():
    return dict(status='Day-To-Day',date='2026-10-21T18:00Z',
                athlete=dict(id='3975',displayName='Fixture Player',position={'abbreviation':'G'}),
                details=dict(type='Ankle',side='Right',detail='Sprain',returnDate='2026-10-21'))


def game():
    return dict(id='1',date='2026-10-22T02:00Z',source='https://www.espn.com/nba/game/_/gameId/1',
                away={'id':'9'},home={'id':'13'})


def values():
    return dict(season=2027,season_type=2,as_of='2026-10-21T18:00Z',coverage='league',
                source='https://www.basketball-reference.com/leagues/NBA_2027_advanced.html',
                players=[dict(id=f'nba:espn:player:{i}',games=1,vorp=v,bpm=None)
                         for i,v in enumerate([-1,0,0,2],1)])


class AvailabilityTests(unittest.TestCase):
    def test_late_utc_game_is_same_day_eastern_and_return_date_does_not_clear_player(self):
        r=build_availability('9','2026-10-22T02:00Z',NOW,[injury()],report_as_of=NOW.isoformat())
        self.assertEqual(r['state'],'reported');self.assertEqual(r['game_date'],'2026-10-21')
        self.assertEqual(r['players'][0]['status'],'Day-To-Day')
        self.assertEqual(r['players'][0]['reason'],'Right · Ankle · Sprain')

    def test_future_and_past_games_never_inherit_current_statuses(self):
        for date,state in [('2026-10-23T00:00Z','pending'),('2026-10-20T00:00Z','expired')]:
            r=build_availability('9',date,NOW,[injury()])
            self.assertEqual(r['state'],state);self.assertEqual(r['players'],[])

    def test_failure_stale_feed_and_empty_report_are_distinct(self):
        self.assertEqual(build_availability('9',game()['date'],NOW,None)['state'],'unavailable')
        self.assertEqual(build_availability('9',game()['date'],NOW,[])['state'],'reported')
        self.assertEqual(build_availability('9',game()['date'],NOW,[injury()],
            report_as_of=(NOW-timedelta(days=2)).isoformat())['state'],'unavailable')

    def test_summary_teams_match_by_id_not_source_order(self):
        g=game()
        def fetch(url):
            if 'injuries?' in url:raise OSError('Unavailable')
            return dict(header={'id':'1'},injuries=[{'team':{'id':'13'},'injuries':[]},
                {'team':{'id':'9'},'injuries':[injury()]}])
        refresh_availability([g],NOW,fetch)
        self.assertEqual(g['away']['availability']['players'][0]['name'],'Fixture Player')
        self.assertEqual(g['home']['availability']['players'],[])

    def test_unavailable_sources_do_not_abort_or_confirm_health(self):
        def fetch(url):raise OSError('Down')
        g=game();refresh_availability([g],NOW,fetch)
        self.assertEqual(g['away']['availability']['state'],'unavailable')

    def test_feed_ids_can_be_read_from_verified_espn_links(self):
        r=injury();r['athlete'].pop('id');r['athlete']['links']=[{'href':'https://www.espn.com/nba/player/_/id/3975/name'}]
        self.assertEqual(normalize_injury(r)['player_id'],'nba:espn:player:3975')


class PlayerValueTests(unittest.TestCase):
    def test_league_percentiles_handle_ties_negative_and_zero_values(self):
        result,meta=player_values(values(),2027,2,NOW)
        self.assertEqual([r['vorp_percentile'] for r in result.values()],[0,50,50,100])
        self.assertEqual(result['nba:espn:player:2']['vorp'],0)
        self.assertEqual(meta['population'],4)

    def test_wrong_season_playoffs_stale_and_future_values_are_rejected(self):
        for key,value in [('season',2026),('season_type',3),('as_of','2026-10-22T00:00Z'),
                          ('as_of','2026-10-15T00:00Z'),('coverage','team')]:
            snap=values();snap[key]=value
            with self.assertRaises(ValueError):player_values(snap,2027,2,NOW)

    def test_incomplete_league_or_duplicate_traded_player_rows_are_rejected(self):
        with self.assertRaises(ValueError):player_values(values(),2027,2,NOW,['nba:espn:player:99'])
        snap=values();snap['players'].append(copy.deepcopy(snap['players'][0]))
        with self.assertRaises(ValueError):player_values(snap,2027,2,NOW)

    def test_unplayed_players_do_not_receive_percentiles(self):
        snap=values();snap['players'].append(dict(id='nba:espn:player:99',games=0,vorp=None))
        result,meta=player_values(snap,2027,2,NOW)
        self.assertNotIn('nba:espn:player:99',result)
        self.assertEqual(meta['population'],4)


if __name__=='__main__':unittest.main()
