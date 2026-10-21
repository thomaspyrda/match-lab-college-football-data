import unittest
from datetime import datetime, timezone
from build_nba_season_leaders import build_leaders, build_historical_leaders, render_page

NOW = datetime(2026,10,21,18,tzinfo=timezone.utc)
TEAMS = {'1':dict(name='One',abbreviation='ONE'),'2':dict(name='Two',abbreviation='TWO')}


def game(key='a',team='1',player='nba:espn:player:1',**changes):
    p=dict(id=player,name='Player '+player,minutes=30,points=20,rebounds=10,assists=5,
           steals=2,blocks=1,tpm=2,fgm=7,ftm=4,turnovers=2,fga=14,tpa=6,fta=5)
    p.update(changes)
    return dict(id=key,date='2026-10-20T23:00:00Z',observed_complete_at='2026-10-21T02:00:00Z',
                season=2027,phase=2,teams={'1':{},'2':{}},players={team:[p]})


def tables(data):
    return {t['key']:t for g in data['groups'] for t in g['tables']}


class LeadersTests(unittest.TestCase):
    def test_current_completed_only_and_traded_player_aggregation(self):
        a=game();b=game('b',team='2');pre=game('pre');pre['phase']=1
        old=game('old');old['season']=2026
        future=game('future');future['observed_complete_at']='2026-10-22T00:00:00Z'
        d=build_leaders({'games':[a,b,pre,old,future]},TEAMS,2027,NOW)
        t=tables(d);self.assertEqual(d['completed_games'],2)
        r=t['points']['rows'][0]
        self.assertEqual((r['value'],r['games'],len(r['teams'])),(40,2,2))
        self.assertEqual(t['points_per_game']['rows'][0]['value'],20)
        self.assertEqual(t['double_doubles']['rows'][0]['value'],2)
        self.assertEqual(t['triple_doubles']['rows'],[])
        self.assertAlmostEqual(t['efg_pct']['rows'][0]['value'],800/14)
        self.assertAlmostEqual(t['ts_pct']['rows'][0]['value'],2000/(2*(14+.44*5)))

    def test_missing_stat_does_not_become_zero_and_dnp_excluded(self):
        d=build_leaders({'games':[game(steals=None),game('b',minutes=0)]},TEAMS,2027,NOW)
        t=tables(d);self.assertEqual(d['players'],1)
        self.assertEqual(t['steals']['rows'],[])
        self.assertEqual(t['points']['rows'][0]['games'],1)

    def test_top_ten_ties_and_attempt_qualification(self):
        g=game();g['players']['1']=[game(player=f'nba:espn:player:{i}',points=20+i)['players']['1'][0] for i in range(12)]
        g['players']['1'][0]['points']=31
        g['players']['1'][0]['fga']=1
        t=tables(build_leaders({'games':[g]},TEAMS,2027,NOW))
        self.assertEqual(len(t['points']['rows']),10)
        self.assertEqual([r['rank'] for r in t['points']['rows'][:3]],[1,1,3])
        self.assertNotIn('nba:espn:player:0',[r['id'] for r in t['fg_pct']['rows']])

    def test_duplicate_appearances_are_rejected(self):
        g=game();g['players']['1']*=2
        with self.assertRaises(ValueError):build_leaders({'games':[g]},TEAMS,2027,NOW)

    def test_historical_stints_combine_and_missing_double_categories_are_omitted(self):
        totals=dict(minutes=30,points=20,rebounds=10,assists=5,steals=2,blocks=1,
                    turnovers=2,fg_made=7,fg_attempts=14,three_made=2,three_attempts=6,
                    ft_made=4,ft_attempts=5)
        player=dict(id='fixture01',name='Traded Player',games=1,totals=totals,
                    league_totals=dict(points=40,rebounds=20,assists=10,steals=4,blocks=2))
        archives={tid:dict(seasons={'2020':dict(season_type='Regular Season',
            games_played=2,players=[player])}) for tid in TEAMS}
        d=build_historical_leaders(archives,TEAMS,2020,NOW)
        t=tables(d)
        self.assertEqual(len(t),26)
        self.assertNotIn('double_doubles',t);self.assertNotIn('triple_doubles',t)
        self.assertEqual(t['points']['rows'][0]['value'],40)
        self.assertEqual(t['points_per_game']['rows'][0]['value'],20)
        self.assertEqual(t['points']['rows'][0]['games'],2)
        self.assertEqual(len(t['points']['rows'][0]['teams']),2)
        self.assertEqual(d['max_team_games'],2)
        self.assertIn('Minimum 2 ',t['points_per_game']['qualification'])
        html=render_page(d,'<head></head><main></main>',[2020,2027],2027)
        self.assertIn('value="/nba/season-leaders/2020/" selected',html)
        self.assertIn('value="/nba/season-leaders/">2026–27',html)
        self.assertNotIn('Double-Doubles',html);self.assertNotIn('Triple-Doubles',html)
        self.assertIn('Historical regular-season totals',html)

    def test_historical_incomplete_or_mismatched_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            build_historical_leaders({},TEAMS,2020,NOW)

    def test_season_selector_keeps_stylesheets_inside_a_closed_head(self):
        data=build_leaders({'games':[game()]},TEAMS,2027,NOW)
        for historical in (False,True):
            data['historical']=historical
            page=render_page(data,'<html><head><title>NBA</title></head><body><main></main></body></html>',[2016,2027],2027)
            self.assertEqual(page.count('</head>'),1)
            self.assertLess(page.index('/sports-research/season-leaders.css'),page.index('</head>'))
            self.assertLess(page.index('/nba/season-leaders/leaders.css?v=3'),page.index('</head>'))
            self.assertLess(page.index('/nba/season-leaders/seasons.js'),page.index('</head>'))
            self.assertLess(page.index('</head>'),page.index('<body>'))


if __name__=='__main__':unittest.main()
