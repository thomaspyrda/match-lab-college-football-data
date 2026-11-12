import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location('morning', Path(__file__).resolve().parents[1] / 'scripts/verify_morning_publication.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MorningPublicationTests(unittest.TestCase):
    def test_eastern_boundary_in_winter_and_summer(self):
        for day, hour in [('2026-11-06', 8), ('2026-07-06', 7)]:
            now = datetime.fromisoformat(day + 'T09:30:00+00:00')
            m.require_collection(day + f'T{hour:02}:15:00+00:00', now)
            with self.assertRaises(ValueError):
                m.require_collection(day + f'T{hour:02}:14:59+00:00', now)

    def test_live_json_must_match_not_just_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data.json').write_text(json.dumps({'games': [1, 2]}))
            m.compare('data.json', root, '', fetch=lambda: {'games': [1, 2]})
            with self.assertRaises(ValueError):
                m.compare('data.json', root, '', fetch=lambda: {'games': [1]})

    def test_pending_boxes_are_not_successful_freshness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'data/cbb/pipeline'
            base.mkdir(parents=True)
            for name in ['results', 'boxes', 'players', 'metrics']:
                (base / (name + '.json')).write_text(json.dumps({'collected_at': '2026-11-06T08:30:00+00:00',
                    'pending': [{'id': 'missing-box'}] if name == 'boxes' else []}))
            with self.assertRaisesRegex(ValueError, 'pending'):
                m.plan('cbb', root, datetime(2026, 11, 6, 9, tzinfo=timezone.utc))


if __name__ == '__main__':
    unittest.main()

