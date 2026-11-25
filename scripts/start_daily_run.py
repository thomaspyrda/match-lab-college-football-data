"""Dispatch the current main workflow explicitly; never replay old cron routing."""
import argparse
import json
import os
import urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('requested', 'morning'), default='morning')
    args = parser.parse_args()
    local = datetime.now(ZoneInfo('America/New_York'))
    cutoff_hour = 17 if args.mode == 'requested' and str(local.date()) == '2026-11-25' else 11
    if not 2 <= local.hour < cutoff_hour:
        raise SystemExit('Outside the 02:00–11:00 Eastern publication window.')
    if args.mode == 'requested':
        request = json.loads((Path(__file__).resolve().parents[1]/'data/automation/primary-request.json').read_text())
        if request.get('date') != str(local.date()) or request.get('cycle') != 'morning':
            raise SystemExit('Primary request is stale or invalid; no data work started.')
    repo = os.environ['GITHUB_REPOSITORY']
    base = 'https://api.github.com/repos/'+repo+'/actions/workflows/coordinate-sport-data.yml'
    headers = {'Authorization': 'Bearer '+os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    with urllib.request.urlopen(urllib.request.Request(base+'/runs?per_page=100', headers=headers), timeout=30) as response:
        runs = json.load(response)['workflow_runs']
    for run in runs:
        if run['head_branch'] != 'main': continue
        if run['status'] in ('queued', 'in_progress', 'waiting', 'pending', 'requested'):
            print('Daily coordinator already active; no duplicate dispatch.')
            return
        created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00')).astimezone(local.tzinfo)
        if created.date() == local.date() and run.get('display_title') == 'morning daily data pipeline':
            print('This morning cycle already started; no duplicate dispatch.')
            return
    body = json.dumps({'ref': 'main', 'inputs': {'sport': 'all', 'morning_date': str(local.date())}}).encode()
    request = urllib.request.Request(base+'/dispatches', data=body, headers={**headers, 'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 204: raise SystemExit('Primary dispatch was not accepted')
    print('Started current main morning coordinator. Completion requires its final live verification.')

if __name__ == '__main__': main()
