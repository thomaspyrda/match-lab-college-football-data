#!/usr/bin/env python3
"""Validate CFB workflow wiring without executing collectors or publishing."""
import re
import subprocess
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.github/workflows'
TARGETS = sorted({'cfb-collect-component.yml', 'cfb-publish-dashboard.yml', 'cfb-publish-markets.yml',
                  'refresh-cfb-results.yml', 'refresh-cfb-strength.yml', 'refresh-cfb-metrics.yml',
                  'refresh-cfb-players.yml', 'refresh-cfb-markets.yml', 'refresh-cfb-context.yml', 'refresh-cfb-metadata.yml',
                  'refresh-cfb-play-mix.yml', 'refresh-cfb-dashboard-schedule-only.yml'} |
                 {'build-team-strength.yml', 'build-cfb-team-pages.yml', 'refresh-fbs-leaders.yml',
                  'frozen-cfb-dashboard-data.yml', 'coordinate-sport-data.yml', 'deploy-pages.yml',
                  'verify-cfb-pipeline.yml', 'test-cfb-component-pipeline.yml'})


def check():
    workflows = {p.name: yaml.load(p.read_text(), Loader=yaml.BaseLoader) for p in BASE.glob('*.yml')}
    for name in TARGETS:
        w = workflows[name]
        assert 'on' in w and isinstance(w.get('jobs'), dict), name
        jobs = w['jobs']
        for jobname, job in jobs.items():
            needs = job.get('needs', [])
            if isinstance(needs, str):
                needs = [needs]
            assert set(needs) <= set(jobs), (name, jobname, needs)
            uses = job.get('uses', '')
            if uses.startswith('./.github/workflows/'):
                target = uses.rsplit('/', 1)[1]
                assert target in workflows, (name, target)
                assert 'workflow_call' in workflows[target]['on'], (name, target, 'not reusable')
            for step in job.get('steps', []):
                if 'run' in step:
                    command = re.sub(r'\$\{\{.*?\}\}', 'TEST_VALUE', step['run'])
                    subprocess.run(['bash', '-n'], input=command, text=True, check=True)
        def visit(job, stack):
            assert job not in stack, (name, stack, job)
            needs = jobs[job].get('needs', [])
            for parent in [needs] if isinstance(needs, str) else needs:
                visit(parent, stack + [job])
        for job in jobs:
            visit(job, [])
    for name in ['cfb-publish-dashboard.yml', 'cfb-publish-markets.yml']:
        assert workflows[name]['jobs']['publish']['concurrency'] == {'group': 'cfb-dashboard-data', 'cancel-in-progress': 'false', 'queue': 'max'}
    model = (BASE / 'build-team-strength.yml').read_text()
    assert 'require-results' in model and 'ranking-inputs' in model
    assert '  deploy:' not in model
    assert "':(exclude)data/cfb/pipeline/**'" in model
    deploy = (BASE / 'deploy-pages.yml').read_text()
    assert "--exclude='data/cfb/pipeline/'" in deploy
    assert 'Publish CFB live markets' in workflows['deploy-pages.yml']['on']['workflow_run']['workflows']
    print(f'Validated {len(TARGETS)} CFB workflow definitions, shell blocks, dependencies, reusable references, and publication scopes.')


if __name__ == '__main__':
    check()
