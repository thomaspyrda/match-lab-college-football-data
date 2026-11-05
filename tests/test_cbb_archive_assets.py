import unittest
from apply_mlb_cbb_team_layout import apply_assets
from publish_cbb_team_archives import JS_VERSION, CSS_VERSION


class ArchiveAssetTests(unittest.TestCase):
    def test_generic_updater_preserves_current_cbb_release_and_removes_legacy_renderer(self):
        css=f'<link rel="stylesheet" href="/sports-research/cbb-team-archive-v1.css?v={CSS_VERSION}" data-cbb-archive="v1">'
        js=f'<script src="/sports-research/cbb-team-archive-v1.js?v={JS_VERSION}" data-cbb-archive="v1"></script>'
        legacy='<script src="/sports-research/mlb-cbb-team-layout-v16.js?v=old" data-archive-layout="mlb-cbb-v1"></script>'
        source='<html><head>'+css+js+'</head><body>'+legacy+'</body></html>'
        updated=apply_assets(source,'cbb')
        self.assertIn(css,updated)
        self.assertIn(js,updated)
        self.assertNotIn('data-archive-layout',updated)
        self.assertEqual(apply_assets(updated,'cbb'),updated)
