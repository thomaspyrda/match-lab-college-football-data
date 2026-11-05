import copy
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("scoring",Path(__file__).resolve().parents[1]/"scripts/cfb_dashboard_scoring_form.py")
scoring=importlib.util.module_from_spec(spec);spec.loader.exec_module(scoring)


class ScoringFormTests(unittest.TestCase):
    def inputs(self):
        games=[dict(id=i, season=2026, seasonType="regular", completed=True,
                    startDate=f"2026-10-{i:02d}T12:00:00Z", homeTeam="A", awayTeam="B",
                    homePoints=30, awayPoints=20) for i in range(1,7)]
        games.append(dict(games[0],id=7,startDate="2026-11-06T12:00:00Z",homePoints=100))
        results=dict(season=2026,collected_at="2026-11-05T12:00:00+00:00",
                     payload=dict(team_games=games,responses={"/teams/fbs?year=2026":[{"school":"A"},{"school":"B"}]}))
        lines=[dict(id=i,lines=[dict(provider="consensus",spread=s,overUnder=t)])
               for i,s,t in [(1,-7,40),(2,-7,49),(3,-10,50),(4,-14,55),(6,3,45)]]
        markets=dict(season=2026,collected_at=results["collected_at"],payload=dict(season_lines=lines,weeks={}))
        data=dict(games=[dict(season=2026,kickoff="2026-11-05T20:00:00Z",
                             away=dict(name="B"),home=dict(name="A"),
                             matchup_metrics=[dict(label="EPA / Play",away_offense=.2)],players=[dict(name="Player")])])
        return data,results,markets

    def test_last_five_completed_games_pushes_signs_and_missing_lines(self):
        data,results,markets=self.inputs()
        scoring.enrich(data,results,markets)
        g=data["games"][0];home=g["home"]["form"]["last5_market"];away=g["away"]["form"]["last5_market"]
        self.assertEqual(home["window_games"],5)
        self.assertEqual(home["ats"],dict(wins=2,losses=1,pushes=1,lined_games=4))
        self.assertEqual(away["ats"],dict(wins=1,losses=2,pushes=1,lined_games=4))
        self.assertEqual(home["ou"],dict(overs=2,unders=1,pushes=1,lined_games=4))
        self.assertEqual(home["ou"],away["ou"])

    def test_scoring_uses_all_completed_scores_and_correct_rank_direction(self):
        data,results,markets=self.inputs()
        scoring.enrich(data,results,markets)
        pair=data["games"][0]["matchup_metrics"][-1]
        self.assertEqual((pair["home_offense"],pair["home_defense"]),(30,20))
        self.assertEqual((pair["home_offense_rank"],pair["home_defense_rank"]),(1,1))
        self.assertEqual((pair["away_offense_rank"],pair["away_defense_rank"]),(2,2))

    def test_missing_markets_are_not_losses_and_existing_metrics_survive(self):
        data,results,_=self.inputs();original=copy.deepcopy(data)
        scoring.enrich(data,results)
        self.assertEqual(data["games"][0]["matchup_metrics"][0],original["games"][0]["matchup_metrics"][0])
        self.assertEqual(data["games"][0]["players"],original["games"][0]["players"])
        self.assertEqual(data["games"][0]["home"]["form"]["last5_market"]["ats"]["lined_games"],0)
        self.assertEqual(data["games"][0]["home"]["form"]["last5_market"]["ats"]["losses"],0)
        self.assertEqual(scoring.enrich(copy.deepcopy(data),results),data)

    def test_non_fbs_teams_do_not_change_fbs_ranks_and_no_sample_is_unranked(self):
        data,results,markets=self.inputs()
        results["payload"]["team_games"].append(dict(id=99,season=2026,completed=True,
            seasonType="regular",startDate="2026-10-01T12:00:00Z",homeTeam="FCS",awayTeam="Other",
            homePoints=99,awayPoints=0))
        scoring.enrich(data,results,markets)
        self.assertEqual(data["games"][0]["matchup_metrics"][-1]["home_offense_rank"],1)
        data["games"][0]["away"]["name"]="Unplayed"
        scoring.enrich(data,results,markets)
        self.assertIsNone(data["games"][0]["matchup_metrics"][-1]["away_offense"])
        self.assertIsNone(data["games"][0]["matchup_metrics"][-1]["away_offense_rank"])
