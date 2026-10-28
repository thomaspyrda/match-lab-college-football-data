"""Refresh layout assets while preserving the active sport-specific renderer."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parent
TAG = 'data-archive-layout="mlb-cbb-v1"'
CSS = '<link rel="stylesheet" href="/sports-research/mlb-cbb-team-layout-draft-v14.css?v=20261028-cbb-backfill-v5" '+TAG+'>'
JS = '<script defer src="/sports-research/mlb-cbb-team-layout-v16.js?v=20261028-cbb-backfill-v5" '+TAG+'></script>'


def apply_assets(text, sport):
    # Real word boundaries remove old tags; escaped literal backslashes did not.
    text = re.sub(r'<link\b[^>]*\bdata-archive-layout="mlb-cbb-v1"[^>]*>', '', text)
    text = re.sub(r'<script\b[^>]*\bdata-archive-layout="mlb-cbb-v1"[^>]*>\s*</script>', '', text)
    if sport == 'cbb' and '/sports-research/cbb-team-archive-v1.js' in text:
        for asset in ('js', 'css'):
            text = re.sub(r'(/sports-research/cbb-team-archive-v1\.'+asset+r')(?:\?[^"<>]*)?', r'\1?v=20261028-cbb-backfill-v5', text)
        return text
    if '</head>' not in text or '</body>' not in text:
        raise ValueError('Missing page shell')
    text = text.replace('</head>', CSS+'</head>', 1).replace('</body>', JS+'</body>', 1)
    assert text.count(TAG) == 2
    return text


def main():
    for sport in ('mlb', 'cbb'):
        paths = list((ROOT / sport / 'teams').glob('*/index.html'))
        if not paths:
            raise RuntimeError(f'No {sport} team pages')
        changed = 0
        for p in paths:
            text = p.read_text()
            if 'id="team-season-data"' not in text:
                raise RuntimeError(f'Missing season payload: {p}')
            updated = apply_assets(text, sport)
            if updated != text:
                p.write_text(updated)
                changed += 1
        print(f'Updated {changed} {sport.upper()} team pages')


if __name__ == '__main__':
    main()
