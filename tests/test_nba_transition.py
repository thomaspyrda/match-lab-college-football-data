import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
import nba_transition as t
class Tests(unittest.TestCase):
    def test_matching_coverage_and_missing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory)/'transition.json'
            checked=datetime.now(timezone.utc)-timedelta(seconds=1)
            doc={'status':'available','season':2027,'checked_at':checked.isoformat(),'teams':{'BOS':{'offensive':{'games':14,'points':17.2},'defensive':{'games':14,'points':18.8}}}}
            dest.write_text(json.dumps(doc))
            with patch.object(t,'DEST',dest):
                self.assertEqual(t.metrics('BOS',14,2027)['transition_points'],17.2)
                self.assertEqual(t.metrics('BOS',14,2027)['opp_transition_points'],18.8)
                self.assertIsNone(t.metrics('BOS',15,2027)['transition_points'])
                self.assertIsNone(t.metrics('BOS',14,2026)['transition_points'])
                self.assertIsNone(t.metrics('BOS',14,2027,checked-timedelta(seconds=1))['transition_points'])
                doc['checked_at']=(checked-timedelta(hours=31)).isoformat();dest.write_text(json.dumps(doc))
                self.assertIsNone(t.metrics('BOS',14,2027)['transition_points'])
    def test_unavailable_does_not_reuse_old_average(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(t,'DEST',Path(directory)/'transition.json'), patch('urllib.request.urlopen',side_effect=OSError('timeout')):
                d=t.refresh(2027)
                self.assertEqual(d['status'],'unavailable')
                self.assertEqual(d['teams'],{})
                self.assertIsNone(t.metrics('BOS',14,2027)['transition_points'])
