import json,unittest
from refresh_cfb_accolades import awards,bowl_wins,conferences,resolver
from cfb_program_accolades import render
from apply_cfb_program_accolades import update_page
from build_cfb_team_pages import ROOT,page
class AccoladeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.teams=json.loads((ROOT/'data/cfb/team-registry.json').read_text())['teams'];cls.resolve=staticmethod(resolver(cls.teams));cls.data=json.loads((ROOT/'data/cfb/program-accolades.json').read_text())
 def test_claimed_and_unclaimed_titles(self):
  for tid,total in [('61',4),('333',18)]:self.assertEqual(sum(x['claimed'] for x in self.data['teams'][tid]['national_titles']),total)
  markup=render('61',self.data);self.assertIn('(not claimed)',markup);self.assertIn('1942',markup)
 def test_heisman_winners_exclude_finalists(self):
  rows,_=awards([(35,2,'HEISMAN MEMORIAL TROPHY\n2023 *Jayden Daniels, LSU, QB 2029\nMichael Penix Jr., Washington, QB 1701\n2025 Heisman Voting\n1. *Fernando Mendoze, Indiana, QB 2362\n2. Diego Pavia, Vanderbilt, QB 1435')],self.resolve)
  self.assertEqual([(r['year'],r['player']) for r in rows],[(2023,'Jayden Daniels'),(2025,'Fernando Mendoza')])
 def test_repeated_award_winners(self):
  rows=[r for r in self.data['teams']['61']['player_awards'] if r['award']=='John Mackey Award' and r['player']=='Brock Bowers']
  self.assertEqual({r['year'] for r in rows},{2022,2023})
 def test_bowl_season_and_championship_exclusion(self):
  rows=bowl_wins([(2,1,'Rose Bowl\nPresent Site: Pasadena, CA\n1/1/2023 Penn St. 35, Utah 21 94873\nCollege Football Playoff National\nChampionship\nPresent Site: Los Angeles\n1/9/2023 Georgia 65, TCU 7 72628')],self.resolve)
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['year'],2022)
 def test_shared_title_with_former_fbs_school(self):
  rows,_=conferences([(18,1,'Big Ten Conference\nYear Champion (Record)\n1905 Michigan (5-0)\nUChicago (7-0)')],self.resolve)
  self.assertTrue(rows[0]['shared'])
 def test_first_round_draft_pick_archive_and_card(self):
  picks=[p for t in self.data['teams'].values() for p in t.get('first_round_draft_picks',[])]
  self.assertEqual(len(picks),self.data['coverage']['nfl_first_round_draft_count'])
  self.assertTrue(all(p['overall_pick']<=32 for p in picks))
  self.assertGreater(len(picks),1500)
  years={p['year'] for p in picks}
  self.assertEqual(min(years),1970);self.assertEqual(max(years),self.data['coverage']['nfl_first_round_draft_through'])
  self.assertIn('NFLDraft:PFR:1970',self.data['sources'])
  markup=render('333',self.data);self.assertIn('NFL First-Round Draft Picks',markup);self.assertIn('Draft Year',markup)
 def test_all_teams_and_unique_entries(self):
  self.assertEqual(set(self.data['teams']),{str(t['id']) for t in self.teams})
  for t in self.data['teams'].values():
   for k,fields in [('bowl_wins',['date','bowl']),('conference_titles',['year','conference']),('national_titles',['year','level']),('player_awards',['year','award','player'])]:
    keys=[tuple(r[f] for f in fields) for r in t[k]];self.assertEqual(len(keys),len(set(keys)),(t['name'],k))
 def test_section_follows_schedule(self):
  t=next(t for t in self.teams if t['name']=='Georgia');html=page(t,{}, {},2026)
  self.assertGreater(html.index('id="programAccolades"'),html.index('id="schedule"'));self.assertIn('href="#programAccolades"',html)
 def test_patch_is_idempotent_and_preserves_season_data(self):
  t=next(t for t in self.teams if t['name']=='Georgia');before=page(t,{}, {},2026);updated=update_page(before,t['id'],self.data)
  self.assertEqual(updated,update_page(updated,t['id'],self.data));self.assertIn('id="teamSeasonData"',updated)
 def test_former_fcs_titles(self):
  t=next(t for t in self.data['teams'].values() if t['name']=='App State');self.assertEqual([r['year'] for r in t['national_titles'] if r['level']=='FCS'],[2007,2006,2005])
if __name__=='__main__':unittest.main()
