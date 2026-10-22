"""Publish MLB league-wide regular-season player totals, preserving archived files."""
import argparse
import concurrent.futures
import json
import math
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'mlb/season-leaders/data'
FIELDS = {
 'hitting': ['gamesPlayed','plateAppearances','atBats','runs','hits','doubles','triples','homeRuns','rbi','stolenBases','baseOnBalls','strikeOuts','avg','obp','slg','ops'],
 'pitching': ['gamesPlayed','gamesStarted','wins','losses','saves','holds','inningsPitched','strikeOuts','baseOnBalls','hits','earnedRuns','era','whip','strikeoutsPer9Inn']}

def normalize(payload, group, year):
    blocks = [b for b in payload.get('stats',[]) if b.get('group',{}).get('displayName') == group]
    if len(blocks) != 1:
        raise ValueError('Missing MLB stats group '+group)
    block = blocks[0]
    splits = block.get('splits',[])
    if not splits or len(splits) != block.get('totalSplits'):
        raise ValueError('Incomplete MLB player coverage')
    rows, seen = [], set()
    for split in splits:
        pid = split['player']['id']
        if pid in seen or str(split['season']) != str(year):
            raise ValueError('Duplicate player or wrong season')
        seen.add(pid)
        stat = split['stat']
        values = {}
        for key in FIELDS[group]:
            raw = stat.get(key)
            if key == 'inningsPitched':
                # Baseball .1/.2 denote outs, not decimal tenths.
                whole, _, fraction = str(raw or '').partition('.')
                if not whole.isdigit() or fraction not in ('','0','1','2'):
                    values[key] = None
                else:
                    values[key] = str(raw)
                    values['outs'] = int(whole)*3+int(fraction or 0)
                continue
            try:
                n = float(raw)
                values[key] = n if math.isfinite(n) else None
            except (ValueError,TypeError):
                values[key] = None
        team = split.get('team',{}).get('name','Multiple teams')
        rows.append(dict(id=pid,name=split['player']['fullName'],
            team='Multiple teams' if split.get('numTeams',1)>1 else team,
            position=split.get('position',{}).get('abbreviation',''),stats=values))
    return rows

def fetch(group, year):
    url = f'https://statsapi.mlb.com/api/v1/stats?stats=season&group={group}&season={year}&sportIds=1&gameType=R&limit=5000&playerPool=ALL'
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url,timeout=60) as response:
                return normalize(json.load(response),group,year)
        except Exception:
            if attempt==2: raise
            time.sleep(attempt+1)

def build(year):
    groups = {group:fetch(group,year) for group in FIELDS}
    snapshots=json.loads((ROOT/'data/mlb/season-snapshots.json').read_text())
    max_games=max((r['games_played'] for r in snapshots['seasons'].get(str(year),{}).values()),default=162)
    if year < datetime.now(timezone.utc).year:
        max_games = max(max_games, 60 if year == 2020 else 162)
    return dict(season=year,updated_at=datetime.now(timezone.utc).isoformat(),
        source='MLB Stats API · regular season only',
        source_url=f'https://www.mlb.com/stats/{year}',
        min_pa=math.ceil(3.1*max_games),min_outs=3*max_games,
        qualification_note='Rate leaderboards use site minimums: 3.1 plate appearances per maximum team game for batting; one inning per maximum team game for pitching. These do not implement every official MLB qualification exception. Counting categories include all players. Multiple-team players use one combined season total, not repeated team splits. Postseason games are excluded.',
        **groups)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--years',nargs='+',type=int,default=[datetime.now(timezone.utc).year])
    parser.add_argument('--refresh',action='store_true',help='Refresh requested years; do not use for archived seasons.')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    years=[year for year in args.years if args.refresh or not (OUT/f'{year}.json').exists() or year==datetime.now(timezone.utc).year]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for year,result in zip(years,pool.map(build,years)):
            dest=OUT/f'{year}.json'
            temp=dest.with_suffix('.tmp')
            temp.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
            temp.replace(dest)
            print(year,len(result['hitting']),len(result['pitching']),flush=True)
    available=sorted(int(p.stem) for p in OUT.glob('*.json') if p.stem.isdigit())
    (OUT/'seasons.json').write_text(json.dumps(available)+'\n')

if __name__=='__main__': main()
