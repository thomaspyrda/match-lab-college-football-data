import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from build_nba_current_schedule import build_team
from nba_current_rankings import build_current_rows
from build_nba_team_rankings import TEAM_INFO, METRIC_LABELS
from refresh_nba_dashboard import location_market_records, scoreboard_day
from refresh_nba_defense import parse
from unittest.mock import patch
from test_nba_current_rankings import fixture

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=json.loads((ROOT/'data/sports/team-registry.json').read_text())


class NBAUpdatesTests(unittest.TestCase):
    def test_paint_is_opponent_points_per_game_and_requires_full_coverage(self):
        game=fixture();game['teams']['2']['paint_points']=40;game['teams']['8']['paint_points']=52
        rows,_=build_current_rows({'games':[game]},REGISTRY,TEAM_INFO,2027,METRIC_LABELS)
        self.assertEqual(next(r for r in rows if r['slug']=='boston-celtics')['metrics']['opp_points_in_paint'],52)
        second=copy.deepcopy(game);second['id']='missing';del second['teams']['8']['paint_points']
        rows,_=build_current_rows({'games':[game,second]},REGISTRY,TEAM_INFO,2027,METRIC_LABELS)
        self.assertIsNone(next(r for r in rows if r['slug']=='boston-celtics')['metrics']['opp_points_in_paint'])

    def test_home_away_signs_neutral_games_and_verified_closing_lines(self):
        game=fixture();game['teams']['2']['points']=110;game['teams']['8']['points']=100
        game['closing_market']={'home_spread':-8,'total':210,'provider':'test','line_type':'closing','source':'https://www.espn.com/nba/game/_/gameId/one','observed_at':'2026-10-21T05:00:00+00:00','evidence':'ESPN pickcenter pointSpread/total close.line'}
        cutoff=datetime(2026,10,22,tzinfo=timezone.utc)
        home=location_market_records([game],'2',cutoff);away=location_market_records([game],'8',cutoff)
        self.assertEqual(home['Home']['ats']['wins'],1)
        self.assertEqual(away['Away']['ats']['losses'],1)
        self.assertEqual(away['Away']['ou']['pushes'],1)
        neutral=copy.deepcopy(game);neutral['neutral']=True
        row=location_market_records([neutral],'2',cutoff)
        self.assertEqual(row['Neutral']['games'],1);self.assertEqual(row['Home']['games'],0)
        del game['closing_market']
        row=location_market_records([game],'2',cutoff)
        self.assertEqual(row['Home']['games'],1);self.assertEqual(row['Home']['ats']['lined_games'],0)

    def test_full_schedule_retains_future_games_and_two_explicit_cup_slots(self):
        data={'requestedSeason':{'year':2027,'type':2},'events':[]}
        lookup={'2':{'slug':'boston-celtics','name':'Boston Celtics'},'8':{'slug':'detroit-pistons','name':'Detroit Pistons'}}
        for i in range(80):
            data['events'].append({'id':str(i),'date':'2026-10-22T01:00Z','season':{'year':2027},'seasonType':{'type':2},'competitions':[{'competitors':[{'team':{'id':'2'},'homeAway':'home'},{'team':{'id':'8'},'homeAway':'away'}],'status':{'type':{'description':'Scheduled'}}}]})
        prior={'0':{'game_id':'0','date':'2026-10-22','result':'W','score_for':110,'score_against':100,'ats_result':'W'}}
        result=build_team(data,'2',lookup,prior,2027)
        self.assertEqual(len(result['games']),82);self.assertEqual(result['pending_cup_games'],2)
        first=next(g for g in result['games'] if g['game_id']=='0')
        self.assertEqual(first['date'],'2026-10-21');self.assertEqual(first['ats_result'],'W')
        future=next(g for g in result['games'] if g['game_id']=='1')
        self.assertNotIn('result',future);self.assertNotIn('score_for',future)
        self.assertEqual(sum(bool(g.get('schedule_pending')) for g in result['games']),2)
        data['events']=data['events'][:4]
        with self.assertRaises(ValueError):build_team(data,'2',lookup,prior,2027)

    def test_optional_future_scoreboard_failure_does_not_block_yesterday(self):
        from datetime import date
        today=date(2026,10,28)
        with patch('refresh_nba_dashboard.get',side_effect=ValueError('empty source')):
            self.assertEqual(scoreboard_day(date(2026,10,30),today),{'events':[]})
            with self.assertRaises(ValueError):scoreboard_day(date(2026,10,27),today)

    def test_position_points_exclude_rank_badges_and_validate_all_150_rows(self):
        teams=[t for t in REGISTRY['teams'] if t['sport']=='nba']
        rows=[]
        for t in teams:
            for p in ['PG','SG','SF','PF','C']:
                cells=[p,t['abbreviation'], '<span id="main_Label2_0">24.7</span><span class="badge">149</span>']+['0']*8
                rows.append('<tr>'+''.join('<td>'+x+'</td>' for x in cells)+'</tr>')
        body='<option selected="selected" value="1">Show data from the entire 2026-27 NBA Season</option>Updated:</strong> 28 October 2026<table id="ContentPlaceHolder1_GridView1"><tr><th>PTS</th></tr>'+''.join(rows)+'</table>'
        data=parse(body,REGISTRY,2027)
        self.assertEqual(data['teams']['boston-celtics']['PG'],24.7)
        with self.assertRaises(ValueError):parse(body.replace(rows[0],''),REGISTRY,2027)
        with self.assertRaises(ValueError):parse(body.replace('2026-27 NBA','2025-26 NBA'),REGISTRY,2027)


if __name__=='__main__':unittest.main()
