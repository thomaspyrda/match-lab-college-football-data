#!/usr/bin/env python3
"""Download the sources used by import_season_details.py (2015–16 to 2025–26)."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen


def fetch(directory):
    directory.mkdir(parents=True, exist_ok=True)
    jobs = [('player-totals.csv', 'https://raw.githubusercontent.com/sumitrodatta/nba-alt-awards/main/2026/Data/Player%20Totals.csv')]
    for year in range(2016, 2027):
        jobs.extend([(f'gamelog_{year}.parquet', f'https://raw.githubusercontent.com/llimllib/nba_data/main/data/gamelog_{year}.parquet'),
                     (f'sdv-team-{year}.csv', f'https://github.com/sportsdataverse/sportsdataverse-data/releases/download/nba_stats_team_boxscores/team_boxscores_{year}.csv')])
    def download(job):
        name, url = job
        with urlopen(url, timeout=60) as response:
            content = response.read()
        temporary = directory / (name + '.tmp')
        temporary.write_bytes(content)
        temporary.replace(directory / name)
        return name
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name in pool.map(download, jobs):
            print(name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    fetch(parser.parse_args().source_dir)
