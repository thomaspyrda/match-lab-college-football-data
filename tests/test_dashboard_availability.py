import unittest
from datetime import datetime,timezone
from refresh_dashboard_availability import players,college_reports
class Availability(unittest.TestCase):
 def setUp(self):self.now=datetime(2026,10,29,22,tzinfo=timezone.utc)
 def row(self,date,**details):return {'athlete':{'id':'1','displayName':'Example Player','position':{'abbreviation':'G'}},'status':'Out','date':date,'details':details}
 def test_old_college_entry_is_not_current_just_because_endpoint_timestamp_is_new(self):
  rows,stale=players([self.row('2020-11-21T18:31Z')],self.now)
  self.assertEqual(rows,[]);self.assertTrue(stale)
 def test_future_report_is_rejected(self):
  rows,_=players([self.row('2026-11-01T18:31Z')],self.now);self.assertFalse(rows)
 def test_current_report_keeps_reported_status_and_reason(self):
  rows,stale=players([self.row('2026-10-29T18:31Z',side='Right',type='Knee')],self.now)
  self.assertFalse(stale);self.assertEqual(rows[0]['status'],'Out');self.assertEqual(rows[0]['reason'],'Right · Knee')
 def test_old_current_long_term_absence_requires_future_return_date(self):
  rows,_=players([self.row('2025-01-01T18:31Z',returnDate='2027-01-01T00:00Z')],self.now);self.assertEqual(len(rows),1)
 def test_partial_college_page_cannot_be_published_as_complete_coverage(self):
  with self.assertRaises(ValueError):college_reports('<title>Report for Oct 29, 2026</title>','cfb',self.now)
