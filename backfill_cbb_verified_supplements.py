"""Import identified official archives after exact season, score and totals checks."""
import concurrent.futures, hashlib, html, json, re, subprocess, tempfile, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from cbb_verified_source import ROOT, save
from backfill_cbb_official_paint import merge

EWU='https://s3.us-east-2.amazonaws.com/sidearm.nextgen.sites/ewu.sidearmsports.com/documents/2017/10/19/16_17MBFinalStatistics.pdf'
def ewu_players(text):
    if '2016-17 Eastern Wash.' not in text or 'All games' not in text or not re.search(r'ALL GAMES\s+22-12',text):raise ValueError('Wrong official season')
    lines=text.splitlines();chunks=[]
    for line in lines:
        if re.match(r'^\s*\d+\s+[A-Za-z].*?\s+\d+-\d+\s+',line):chunks.append(line.strip())
        elif chunks and line.strip() and not re.search(r'Team|Total|Opponents|Score by',line):chunks[-1]+=' '+line.strip()
        elif chunks:break
    rows=[]
    for line in chunks:
        m=re.match(r'^(\d+)\s+(.+?),\s+(.+?)\s+(\d+)-(\d+)\s+(.+)$',line)
        if not m:raise ValueError('Unknown player row')
        jersey,last,first,gp,starts,raw=m.groups();gp=int(gp);values=raw.split()
        if len(values)!=20:raise ValueError('Unknown official stat columns '+str(len(values)))
        fgm,fga=map(int,values[2].split('-'));tpm,tpa=map(int,values[4].split('-'));ftm,fta=map(int,values[6].split('-'))
        points=int(values[18]);reb=int(values[10]);assists=int(values[14]);to=int(values[15]);blk=int(values[16]);stl=int(values[17])
        if 2*fgm+tpm+ftm!=points or not 0<gp<=34 or not 0<=tpm<=fgm<=fga or not 0<=tpm<=tpa or not 0<=ftm<=fta:raise ValueError('Official player arithmetic mismatch')
        stats={'gamesPlayed':gp,'points':points,'rebounds':reb,'avgMinutes':int(values[0])/gp,
            'avgPoints':points/gp,'avgRebounds':reb/gp,'avgAssists':assists/gp,'avgTurnovers':to/gp,'avgSteals':stl/gp,'avgBlocks':blk/gp}
        for made,att,label in [(fgm,fga,'fieldGoalPct'),(tpm,tpa,'threePointFieldGoalPct'),(ftm,fta,'freeThrowPct')]:
            if att:stats[label]=100*made/att
        rows.append({'id':'official-ewu-2017-'+jersey,'name':first+' '+last.title(),'position':None,'stats':stats})
    if len(rows)!=14 or sum(p['stats']['points'] for p in rows)!=2695:raise ValueError('Incomplete official player table')
    return sorted(rows,key=lambda p:-p['stats']['avgPoints'])

def duke_paint(body):
    # Only the first full-game box; never first/second-half boxes.
    blocks=re.findall(r'<pre\b[^>]*>(.*?)</pre>',body,re.S|re.I)
    for block in blocks:
        text=html.unescape(re.sub('<[^>]+>',' ',block)).replace('\r','')
        if 'Official Basketball Box Score' not in text or re.search(r'Official Basketball Box Score\s*--',text):continue
        vis=re.search(r'^\s*VISITORS:\s*(.*?)\s*$',text,re.M);home=re.search(r'^\s*HOME TEAM:\s*(.*?)\s*$',text,re.M)
        paint=re.search(r'Points in the paint-([^,\s]+)\s+(\d+),\s*([^.,\s]+)\s+(\d+)\.',text,re.I)
        date=re.search(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',text)
        if not all((vis,home,paint,date)):continue
        names=[re.sub(r'\s+\(?\d+-\d+.*$','',v[1]).strip() for v in (vis,home)]
        own=next((i for i,n in enumerate(names) if n.lower()=='duke'),None)
        if own is None:continue
        scores={re.sub(r'[^a-z]','',n.lower()):int(v) for n,v in re.findall(r'^\s*(.*?)\.{2,}\s+[\d\s]+-\s*(\d+)\s*$',text.split('Score by Periods')[-1],re.M)}
        final=[scores.get(re.sub(r'[^a-z]','',n.lower())) for n in names]
        if None in final:continue
        codes=[paint[1].upper(),paint[3].upper()];values=[int(paint[2]),int(paint[4])]
        if not any(c in ('DU','DUKE') for c in codes):continue
        i=next(i for i,c in enumerate(codes) if c in ('DU','DUKE'));a,b=values[i],values[1-i]
        if not 0<a<=final[own] or not 0<b<=final[1-own] or a%2 or b%2:continue
        totals=re.findall(r'^\s*Totals\.{2,}\s+(\d+)-(\d+)\s+(\d+)-(\d+)\s+(\d+)-(\d+)\s+([^\n]+)',text,re.M)
        if len(totals)!=2:continue
        if any(2*int(row[0])+int(row[2])+int(row[4])!=score for row,score in zip(totals,final)):continue
        if a>2*(int(totals[own][0])-int(totals[own][2])) or b>2*(int(totals[1-own][0])-int(totals[1-own][2])):continue
        stamp=next((datetime.strptime(date[0],f).date().isoformat() for f in ['%m/%d/%y'] if len(date[0].split('/')[-1])==2),None)
        if stamp:return {'date':stamp,'points':final[own],'opponent_points':final[1-own],'paint_for':a,'paint_against':b,'format':'Official whole-game StatCrew box; both scoring equations and paint bounds verified'}
    return None

def main():
    report={}
    path=ROOT/'data/cbb/teams/eastern-washington-eagles.json';a=json.loads(path.read_text());s=a['seasons']['2017']
    if not s.get('players'):
        with urllib.request.urlopen(EWU,timeout=45) as response:pdf=response.read()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.pdf';p.write_bytes(pdf);text=subprocess.check_output(['pdftotext','-f','2','-l','2','-layout',str(p),'-'],text=True)
        players=ewu_players(text);games={g['id']:g for ph in s['phases'].values() for g in ph.get('games',[]) if g.get('status')=='final' and g.get('points',0)+g.get('opponent_points',0)>2}
        assert len(games)==34 and sum(g['points'] for g in games.values())==2695
        s['players']=players;s['player_stats_source']={'scope':'full season, regular season and postseason','complete':True,'games':34,'expected_games':34,'url':EWU,'page':2,'sha256':hashlib.sha256(pdf).hexdigest(),'method':'Official final full-season player table; 34 games and 2695 points match archive; all player scoring arithmetic checked'}
        s.setdefault('sources',[]).append({'name':'Eastern Washington official 2016-17 final player statistics','url':EWU});save(path,a);report['ewu_players']=len(players)
    official=json.loads((ROOT/'data/cbb/official-paint-observations.json').read_text())['records'];known={(r['team'],str(r['game_id'])) for r in official if not r.get('conflict')}
    d=json.loads((ROOT/'data/cbb/teams/duke-blue-devils.json').read_text());records=[]
    def one(item):
        year,g=item;day=datetime.fromisoformat(g['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date()
        url=f'https://static.goduke.com/custompages/stats/{int(year)-1}-{str(year)[-2:]}/basketball-m/du{day:%m%d}.htm'
        try:
            with urllib.request.urlopen(url,timeout=20) as response:box=duke_paint(response.read().decode('utf-8','replace'))
            if box and box['date']==day.isoformat() and box['points']==g['points'] and box['opponent_points']==g['opponent_points']:
                return {**box,'year':year,'game_id':str(g['id']),'team':'duke-blue-devils','source':url}
        except Exception:return None
    gap_years={r['season'] for r in json.loads((ROOT/'data/cbb/paint-coverage-report.json').read_text())['remaining_gaps'] if r['team']=='duke-blue-devils'}
    todo=[(year,g) for year,s in d['seasons'].items() if year in gap_years for g in s['phases']['regular']['games'] if g.get('status')=='final' and ('duke-blue-devils',str(g['id'])) not in known]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:records=[r for r in pool.map(one,todo) if r]
    identities={str(t['espn_id']):t['slug'] for t in json.loads((ROOT/'data/sports/team-registry.json').read_text())['teams'] if t['sport']=='cbb'}
    own_count=len(records)
    for r in list(records):
        game=next(g for g in d['seasons'][r['year']]['phases']['regular']['games'] if str(g['id'])==r['game_id'])
        opponent=identities.get(str(game.get('opponent_id')))
        if opponent:records.append({**r,'team':opponent,'points':r['opponent_points'],'opponent_points':r['points'],'paint_for':r['paint_against'],'paint_against':r['paint_for']})
    if records:
        with tempfile.TemporaryDirectory() as tmp:
            save(Path(tmp)/'official-paint-shard-0.json',{'records':records,'audit':{'verified_static_statcrew':len(records)},'teams':[]})
            merge(SimpleNamespace(input_dir=tmp,shards=1))
    counts=Counter()
    for p in (ROOT/'data/cbb/teams').glob('*.json'):
        arc=json.loads(p.read_text())
        for year,season in arc['seasons'].items():
            if not 2016<=int(year)<=2026 or not any(g.get('status')=='final' and g.get('points',0)+g.get('opponent_points',0)>2 for ph in season.get('phases',{}).values() for g in ph.get('games',[])):continue
            counts['eligible_team_seasons']+=1
            if not any((p.get('stats') or {}).get('gamesPlayed',0)>0 for p in season.get('players') or []):counts['blank_player_tables']+=1
            if season.get('player_stats_source',{}).get('complete') is False:counts['explicit_partial_player_tables']+=1
    report['player_table_coverage']=dict(counts)
    report.update(duke_game_boxes_attempted=len(todo),duke_paint_games_recovered=own_count,opponent_observations_added=len(records)-own_count);save(ROOT/'data/cbb/verified-supplements-report.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':main()
