"""Build read-only MLB ranking views from official regular-season snapshots.

Never writes source snapshots or team archives. Overall: run differential/game;
batting: OPS; pitching: ERA (lower is better). No opponent/park adjustments.
"""
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'mlb/rankings/data/mlb-team-rankings.json'
LABELS = {'run_diff_per_game':'Run Diff/G','runs_per_game':'R/G',
          'runs_allowed_per_game':'RA/G','ops':'OPS','batting_average':'AVG',
          'on_base_percentage':'OBP','slugging_percentage':'SLG',
          'home_runs':'HR','home_runs_per_game':'HR/G','strikeout_rate':'Batting K%',
          'era':'ERA','whip':'WHIP','opponent_average':'Opp AVG',
          'strikeouts_per_9':'K/9','overall_sd':'Overall SD',
          'offense_sd':'Batting SD','defense_sd':'Pitching SD',
          'games_played':'GP','runs_scored':'Runs','runs_allowed':'Runs Allowed'}
LOWER = ['runs_allowed_per_game','strikeout_rate','era','whip','opponent_average','runs_allowed']

def number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None

def rate(rows):
    averages = {}
    for category, key, lower in [('overall','run_diff_per_game',False),
                                  ('offense','ops',False),('defense','era',True)]:
        eligible = [r for r in rows if r['games_played'] > 0 and r['metrics'][key] is not None]
        values = [r['metrics'][key] for r in eligible]
        mean = statistics.mean(values) if values else None
        sd = statistics.pstdev(values) if values else None
        averages[key] = mean
        for row in rows:
            row['ranks'][category] = None
            row['ratings'][category+'_sd'] = None
        for row in eligible:
            value = row['metrics'][key]
            row['ranks'][category] = 1 + sum(v < value if lower else v > value for v in values)
            row['ratings'][category+'_sd'] = round((mean-value if lower else value-mean)/sd, 4) if sd else 0.0
    return averages

def build(snapshot, registry):
    identities = {t['slug']:t for t in registry['teams'] if t.get('sport') == 'mlb'}
    if len(identities) != 30:
        raise ValueError('MLB registry must contain exactly 30 teams')
    result = dict(schema_version=1, generated_at=datetime.now(timezone.utc).isoformat(),
                  default_season=max(snapshot['seasons'], key=int), metric_labels=LABELS,
                  lower_is_better=LOWER, source='MLB Stats API · regular season only', seasons={})
    for year, teams in snapshot['seasons'].items():
        if set(teams) != set(identities):
            raise ValueError('Incomplete MLB season '+year)
        rows = []
        for slug, source in teams.items():
            identity = identities[slug]
            gp = int(source['games_played'])
            if gp != source['wins']+source['losses']+source.get('ties',0):
                raise ValueError('Record does not reconcile: '+year+' '+slug)
            metrics = {k:number(source.get('team_stats',{}).get(k)) for k in
                       ['batting_average','on_base_percentage','slugging_percentage',
                        'home_runs','strikeout_rate','era','whip','opponent_average','strikeouts_per_9']}
            rs, ra = number(source.get('runs_scored')), number(source.get('runs_allowed'))
            obp, slg = metrics['on_base_percentage'], metrics['slugging_percentage']
            metrics.update(games_played=gp, runs_scored=rs if gp else None,
                           runs_allowed=ra if gp else None,
                           runs_per_game=rs/gp if gp and rs is not None else None,
                           runs_allowed_per_game=ra/gp if gp and ra is not None else None,
                           run_diff_per_game=(rs-ra)/gp if gp and rs is not None and ra is not None else None,
                           ops=round(obp+slg,3) if obp is not None and slg is not None else None,
                           home_runs_per_game=metrics['home_runs']/gp if gp and metrics['home_runs'] is not None else None)
            if not gp:
                metrics = {k:None for k in metrics}
            record = f"{source['wins']}–{source['losses']}"
            if source.get('ties'):
                record += f"–{source['ties']}"
            rows.append(dict(slug=slug,team=identity['name'],abbreviation=identity['abbreviation'],
                             logo=identity['logo'],conference=identity.get('conference'),
                             division=identity.get('division'),record=record,games_played=gp,
                             metrics=metrics,ratings={},ranks={}))
        averages = rate(rows)
        result['seasons'][year] = dict(label=year,status='complete' if all(
            t.get('status')=='complete' for t in teams.values()) else 'in_progress',
            team_count=30,ranked_teams=sum(r['games_played']>0 for r in rows),
            league_average=averages, source_url=f'https://www.mlb.com/stats/team/{year}',
            source_name='MLB Stats API regular-season team statistics',
            data_updated_at=max((t.get('team_stats_updated_at') or snapshot.get('generated_at','') for t in teams.values()),default=None),
            source_note='Overall sorts by run differential per game; Batting by OPS; Pitching by ERA (lower is better). OPS is OBP + SLG from the source’s rounded rates. SD compares each team with the unweighted mean of eligible teams in that season; positive is better. Ties share a rank. No opponent, ballpark, recency, fielding or baserunning adjustment. Postseason games are excluded. Supporting columns do not change the default ranking.',
            teams=sorted(rows,key=lambda r:(r['ranks']['overall'] is None,r['ranks']['overall'] or 0,r['team'])))
    played=[y for y,season in result['seasons'].items() if season['ranked_teams']>0]
    if played: result['default_season']=max(played,key=int)
    return result

def main():
    snapshots = json.loads((ROOT/'data/mlb/season-snapshots.json').read_text())
    registry = json.loads((ROOT/'data/sports/team-registry.json').read_text())
    result = build(snapshots,registry)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,separators=(',',':'),ensure_ascii=False)+'\n')
    print(f"Built {len(result['seasons'])} seasons / {sum(s['team_count'] for s in result['seasons'].values())} team-seasons")

if __name__ == '__main__':
    main()
