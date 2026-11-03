#!/usr/bin/env python3
"""Validate CBB workflow wiring without dispatching or publishing."""
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[1]


def main():
    files = list((ROOT / '.github/workflows').glob('*.yml'))
    docs = {path.name: yaml.safe_load(path.read_text()) for path in files}
    names = {doc['name'] for doc in docs.values()}
    for filename, doc in docs.items():
        if filename not in ["build-cbb-metric-ranks.yml","build-cbb-strength.yml","cbb-collect-component.yml","cbb-historical-archives.yml","cbb-publish-markets.yml","cbb-publish-team-pages.yml","cbb-team-archives.yml","coordinate-sport-data.yml","deploy-pages.yml","refresh-cbb-boxes.yml","refresh-cbb-dashboard.yml","refresh-cbb-metrics.yml","refresh-cbb-players.yml","refresh-cbb-rosters.yml","refresh-cbb-season-leaders.yml","test-cbb-component-pipeline.yml","verify-cbb-pipeline.yml"]:
            continue
        trigger = doc.get('on', doc.get(True, {}))
        for name in (trigger.get('workflow_run') or {}).get('workflows', []):
            assert name in names, filename + ': unknown upstream workflow ' + name
        for job in doc.get('jobs', {}).values():
            uses = job.get('uses', '')
            if uses.startswith('./.github/workflows/'):
                target = docs[Path(uses).name]
                assert 'workflow_call' in target.get('on', target.get(True, {})), uses + ': not reusable'
            steps = job.get('steps', [])
            for step in steps:
                script = step.get('run', '')
                if 'git push origin HEAD:main' in script:
                    assert 'git rebase origin/main' in script and 'for attempt in' in script, filename + ': unsafe publication retry'
    publishers = ['refresh-cbb-dashboard.yml', 'cbb-publish-team-pages.yml', 'refresh-cbb-season-leaders.yml',
                  'build-cbb-metric-ranks.yml', 'build-cbb-strength.yml', 'cbb-publish-markets.yml']
    for filename in publishers:
        doc = docs[filename]
        assert doc['jobs']['deploy']['uses'] == './.github/workflows/deploy-pages.yml', filename + ': missing explicit deployment'
        assert doc['permissions']['pages'] == 'write' and doc['permissions']['id-token'] == 'write'
    assert "--exclude='data/cbb/pipeline/'" in (ROOT / '.github/workflows/deploy-pages.yml').read_text()
    assert docs['refresh-cbb-dashboard.yml']['jobs']['publish']['concurrency']['group'] == docs['cbb-publish-markets.yml']['jobs']['publish']['concurrency']['group']
    print('CBB reusable calls, source triggers, writer locks, safe retries and explicit deployment checks passed')


if __name__ == '__main__':
    main()
