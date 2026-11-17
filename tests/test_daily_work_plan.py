import importlib.util,json,tempfile,unittest,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import daily_work_plan as m

NOW=datetime(2026,11,17,8,tzinfo=timezone.utc)
class Tests(unittest.TestCase):
 def test_serialized_scores_do_not_make_every_day_changed(self):
  observed=m.espn_finals({'events':[{'id':'g','competitions':[{'status':{'type':{'completed':True}},'competitors':[{'team':{'id':'a'},'score':'98'},{'team':{'id':'b'},'score':'95'}]}]}]})
  self.assertEqual(m.changed_finals(observed,json.loads(json.dumps(observed))),{})
  self.assertTrue(m.changed_finals({'g':[['a','99'],['b','95']]},observed))
 def test_expiring_window_does_not_invent_new_games(self):
  self.assertFalse(m.changed_finals({}, {'old':['1','0']}))
 def test_unavailable_source_cannot_authorize_skip(self):
  with tempfile.TemporaryDirectory() as tmp:
   def fail(*args):raise OSError('source unavailable')
   plan=m.make_plan(Path(tmp),NOW,fail)
   for item in plan['sports'].values():
    self.assertTrue(item['statistics']);self.assertEqual(item['status'],'source_unavailable')
 def test_failed_sport_never_advances_watermark(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/m.PLAN).parent.mkdir(parents=True)
   (root/m.PLAN).write_text(json.dumps({'checked_at':NOW.isoformat(),'checked_through':'2026-11-16','sports':{s:{'status':'checked','statistics':True,'observed_finals':{'g':[1,0]}} for s in ('nba','cbb')}}))
   m.checkpoint(root,{'nba':'success','cbb':'failure'})
   state=m.read(root/m.STATE);self.assertIn('nba',state['sports']);self.assertNotIn('cbb',state['sports'])
 def test_offday_proof_expires_and_rejects_new_scores(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/m.PLAN).parent.mkdir(parents=True)
   (root/m.STATE).write_text(json.dumps({'sports':{'nba':{'finals':{'g':[1,0]}}}}))
   plan={'checked_at':NOW.isoformat(),'sports':{'nba':{'status':'checked','statistics':False,'observed_finals':{'g':[1,0]}}}}
   (root/m.PLAN).write_text(json.dumps(plan))
   self.assertTrue(m.verified_no_change('nba',root,NOW));self.assertFalse(m.verified_no_change('nba',root,NOW+timedelta(days=1)))
   plan['sports']['nba']['observed_finals']['g']=[2,0];(root/m.PLAN).write_text(json.dumps(plan))
   self.assertFalse(m.verified_no_change('nba',root,NOW))

if __name__=='__main__':unittest.main()
