"""Import provider-reported season records and strictly matched pregame line snapshots.
Usage: python backfill_cbb_markets.py --source-dir /tmp/cbb-sources
No synthetic lines, fuzzy team matches, or extrapolated full-season records.
"""
import argparse,csv,html,json,re,unicodedata
from collections import defaultdict,Counter
from datetime import datetime,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def norm(v):
    v=unicodedata.normalize('NFKD',str(v)).encode('ascii','ignore').decode().lower().replace('saint','st').replace('state','st')
    return re.sub('[^a-z0-9]','',v)
def load(p):return json.loads(p.read_text())
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,separators=(',',':'),ensure_ascii=False)+'\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-dir',type=Path,required=True);args=ap.parse_args();src=args.source_dir
    teams=[t for t in load(ROOT/'data/sports/team-registry.json')['teams'] if t['sport']=='cbb'];by_slug={t['slug']:t for t in teams};names=defaultdict(set)
    for t in teams:
        for name in [t['slug'],t['name'],t['short_name'],*t.get('aliases',[])]:
            if name:names[norm(name)].add(t['slug'])
    mapping=load(ROOT/'data/cbb/tournament-team-map.json')['teams']
    for x in mapping.values():
        if x.get('slug') in by_slug:names[norm(x['name'])].add(x['slug'])
    manual={'Albany':'ualbany-great-danes','Appalachian St.':'app-state-mountaineers','Nicholls State':'nicholls-colonels','Grambling State':'grambling-tigers','New Orleans':'lsu-new-orleans-privateers','Miami-Florida':'miami-hurricanes','Tenn-Martin':'ut-martin-skyhawks','UL Monroe':'ul-monroe-warhawks','Mississippi':'ole-miss-rebels','IUPUI':'iu-indianapolis-jaguars','LIU Brooklyn':'long-island-university-sharks','LIU':'long-island-university-sharks','Seattle':'seattle-u-redhawks','FDU':'fairleigh-dickinson-knights','Pennsylvania':'pennsylvania-quakers','USC Upstate':'south-carolina-upstate-spartans','Central CT':'central-connecticut-blue-devils','Southern':'southern-jaguars','American U.':'american-university-eagles','Massachusetts':'massachusetts-minutemen','SFA':'stephen-f-austin-lumberjacks','Texas A&M-CC':'texas-am-corpus-christi-islanders','East Texas A&M':'east-texas-am-lions','St. Francis (PA)':'saint-francis-red-flash','St. Thomas (MN)':'st-thomas-tommies'}
    # Resolve supplied aliases against current identities, failing on a bad alias rather than guessing.
    for k,v in manual.items():
        if v in by_slug:names[norm(k)]={v}
    def resolve(*values):
        for value in values:
            if value in by_slug:return value
            matches=names.get(norm(value),set())
            if len(matches)==1:return next(iter(matches))
        return None
    db={slug:{'source':'Covers season summaries and JDSB123 pregame odds archive','seasons':{},'games':{}} for slug in by_slug};unmatched=Counter();summary_counts={}
    for year in range(2016,2027):
        text=(src/f'covers{year}.html').read_text();tables=dict(re.findall(r'<table id="([^"]+)"(.*?)</table>',text,re.S));assert 'RegularSeason' in tables
        for tabname,tab in tables.items():
            if tabname!='RegularSeason':continue # PostSeason overlaps for recent years; never double count.
            for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',tab,re.S):
                cells=re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.S)
                if len(cells)<5:continue
                provider_slug=re.search(r'/teams/main/([^"/]+)',cells[0]).group(1);label=html.unescape(re.search(r'alt="([^"]+)"',cells[0]).group(1))
                slug=resolve(provider_slug,label)
                if not slug:unmatched[label]+=1;continue
                def record(i):return [int(x) for x in re.findall(r'\d+',re.sub('<[^>]+>','',cells[i]))]
                ats,ou,su=record(1),record(4),record(3)
                assert len(ats)==len(ou)==3 and len(su)==2
                if not sum(ats) and not sum(ou):continue
                db[slug]['seasons'][str(year)]={'ats':ats,'ou':ou,'source':f'https://www.covers.com/sport/basketball/ncaab/statistics/team-betting/{year-1}-{year}','provider_su':su,'coverage':'provider-reported season table; some historical seasons omit postseason lines'}
        summary_counts[year]=sum(str(year) in x['seasons'] for x in db.values())
    # Match archive games by exact date and two verified school identities.
    lookup=defaultdict(list)
    for slug in by_slug:
        a=load(ROOT/f'data/cbb/teams/{slug}.json')
        for year,season in a['seasons'].items():
            for phase in ('regular','postseason'):
                for g in season['phases'].get(phase,{}).get('games',[]):
                    opponent=resolve(g.get('opponent'),g.get('opponent_name'))
                    if not opponent or g.get('status')!='final':continue
                    day=datetime.fromisoformat(g['date'].replace('Z','+00:00')).date()
                    lookup[(year,day,frozenset([slug,opponent]))].append((slug,g))
    audit=Counter()
    for kind in ('spreads','totals'):
        for row in csv.DictReader((src/f'{kind}-canonical.csv').open()):
            home=resolve(row['home_team'],row['home_team_canonical']);away=resolve(row['away_team'],row['away_team_canonical'])
            if not home or not away:
                audit['unmatched_odds_team']+=1;continue
            start=datetime.fromisoformat(row['commence_time'].replace('Z','+00:00'));stamp=datetime.fromisoformat(row['timestamp'].replace('Z','+00:00'))
            if not 0<=(start-stamp).total_seconds()<=3600:audit['not_near_pregame']+=1;continue
            entries=list({(slug,g['id']):(slug,g) for slug,g in lookup.get((row['season'],start.date(),frozenset([home,away])),[])}.values())
            if not entries:audit['no_archive_game']+=1;continue
            # A school's side must match exactly one game on this date; duplicate games are rejected.
            counts=Counter(slug for slug,g in entries)
            for slug,g in entries:
                if counts[slug]!=1:audit['ambiguous_game']+=1;continue
                out=db[slug]['games'].setdefault(row['season'],{}).setdefault(g['id'],{})
                if kind=='spreads':
                    line=float(row['spread'])*(1 if slug==home else -1);margin=g['points']-g['opponent_points']+line
                    out.update(spread=line,ats='W' if margin>0 else 'L' if margin<0 else 'P')
                else:
                    line=float(row['total']);margin=g['points']+g['opponent_points']-line
                    out.update(total=line,ou='O' if margin>0 else 'U' if margin<0 else 'P')
                out.update(bookmaker=row['bookmaker'],observed_at=row['timestamp'],source='https://github.com/JDSB123/ncaam-historical-data',line_type='pregame snapshot')
                audit[kind+'_team_games']+=1
    for slug,data in db.items():save(ROOT/f'data/cbb/markets/{slug}.json',data)
    report={'season_summaries':summary_counts,'unmapped_summary_names':dict(unmatched),'game_lines':dict(audit),'sources':['https://www.covers.com/sport/basketball/ncaab/statistics/team-betting/2015-2016','https://github.com/JDSB123/ncaam-historical-data'],'method':'Season records retain Covers reported totals. They are not mixed with schedule-level pregame snapshot records. No closing-line claim.'}
    save(ROOT/'data/cbb/market-backfill-report.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
