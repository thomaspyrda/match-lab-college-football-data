"""Validate sourced paint aggregates and publish the remaining historical gaps."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import backfill_cbb_official_paint as base

def main():
    metrics=base.load(base.R/'data/cbb/opponent-metrics.json')['seasons']
    records=base.load(base.R/'data/cbb/official-paint-observations.json')['records']
    groups=defaultdict(dict);conflicts=0
    for r in records:
        if r.get('conflict'):conflicts+=1;continue
        assert r['paint_for']%2==r['paint_against']%2==0
        assert 0<=r['paint_for']<=r['points'] and 0<=r['paint_against']<=r['opponent_points']
        groups[r['year'],r['team']][r['game_id']]=r
    years=defaultdict(Counter);gaps=[];verified=0
    for slug in base.load(base.R/'data/cbb/official-paint-sources.json')['teams']:
        archive=base.load(base.R/f'data/cbb/teams/{slug}.json')
        for year,season in archive['seasons'].items():
            if not 2016<=int(year)<=2026:continue
            games={g['id']:g for g in season.get('phases',{}).get('regular',{}).get('games',[]) if base.completed_stat_game(g)}
            if len(games)<10:continue
            years[year]['eligible_team_seasons']+=1
            entry=metrics.get(year,{}).get(slug,{});values=entry.get('values',{})
            samples=[r for gid,r in groups[year,slug].items() if gid in games and r['points']==games[gid]['points'] and r['opponent_points']==games[gid]['opponent_points']]
            available=all(values.get(k) is not None for k in ['Points in the Paint','Points in the Paint Allowed'])
            if available:
                years[year]['covered_team_seasons']+=1
                sample=entry.get('metric_samples',{}).get('Points in the Paint',{})
                assert sample.get('games',0)>=10 and sample['games']/sample['expected_games']>=.95,(slug,year,sample)
                if sample.get('method','').startswith('Official'):
                    assert len(samples)==sample['games'] and len(games)==sample['expected_games'],(slug,year)
                    for label,key in [('Points in the Paint','paint_for'),('Points in the Paint Allowed','paint_against')]:
                        assert abs(values[label]-sum(r[key] for r in samples)/len(samples))<1e-8,(slug,year,label)
                    verified+=1;years[year]['official_archive_team_seasons']+=1
                else:years[year]['other_verified_provider_team_seasons']+=1
            else:
                years[year]['unfilled_team_seasons']+=1
                gaps.append({'team':slug,'season':year,'verified_official_games':len(samples),'expected_games':len(games),'missing_games_for_95_percent':max(0,__import__('math').ceil(.95*len(games))-len(samples))})
    report={'updated_at':datetime.now(timezone.utc).isoformat(),'scope':'2015-16 through 2025-26; regular season including conference tournaments; at least 10 games and 95% verified coverage','years':dict(sorted(years.items())),'totals':dict(sum(years.values(),Counter())),'official_team_game_observations':len(records),'conflicting_observations_excluded':conflicts,'official_aggregates_validated':verified,'remaining_gaps':sorted(gaps,key=lambda x:(x['missing_games_for_95_percent'],x['season'],x['team']))}
    base.save(base.R/'data/cbb/paint-coverage-report.json',report)
    print({k:v for k,v in report.items() if k not in ['remaining_gaps','years']})

if __name__=='__main__':main()
