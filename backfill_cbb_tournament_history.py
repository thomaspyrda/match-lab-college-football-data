"""Resolve season tournament results from games and bracket slots, retaining standings.
Kaggle March Machine Learning Mania CSV cache through 2025; ESPN scoreboard for 2026.
"""
import argparse,csv,json,re,urllib.request
from pathlib import Path
from collections import defaultdict,Counter
ROOT=Path(__file__).resolve().parent
SRC='https://github.com/KernelMcGregor/2026MMMLM/tree/main/Data'
def load(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,separators=(',',':'),ensure_ascii=False)+'\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-dir',type=Path,required=True);ap.add_argument('--fetch-2026',action='store_true');args=ap.parse_args()
    def read(n):return list(csv.DictReader((args.source_dir/(n+'.csv')).open(encoding='utf-8-sig')))
    teams={t['slug']:t for t in load(ROOT/'data/sports/team-registry.json')['teams'] if t['sport']=='cbb'}
    mapping=load(ROOT/'data/cbb/tournament-team-map.json')['teams'];ids={k:v['slug'] for k,v in mapping.items() if v.get('slug') in teams}
    ids['1237']='iu-indianapolis-jaguars';ids['1477']='east-texas-am-lions'
    names={k:v['name'] for k,v in mapping.items()}
    def label(i):return teams[ids[i]]['short_name'] if i in ids else names.get(i,i)
    conf=load(ROOT/'data/cbb/conference-tournament-results.json');national=load(ROOT/'data/cbb/tournament-results.json')
    scores={(g['Season'],g['DayNum'],g['WTeamID'],g['LTeamID']):g for g in read('MRegularSeasonCompactResults')}
    groups=defaultdict(list);membership=defaultdict(dict)
    for r in read('MTeamConferences'):membership[r['Season']][r['TeamID']]=r['ConfAbbrev']
    for r in read('MConferenceTourneyGames'):
        if 2016<=int(r['Season'])<=2025:groups[r['Season'],r['ConfAbbrev']].append(r)
    def game_result(g,tid,champ=False,prefix='',rd=None):
        win=g['WTeamID']==tid;op=g['LTeamID'] if win else g['WTeamID'];score=''
        if 'WScore' in g:score=', '+(g['WScore']+'–'+g['LScore'] if win else g['LScore']+'–'+g['WScore'])
        return prefix+('Champion — Defeated ' if champ else ('Eliminated'+(' in '+rd if rd else '')+' — Lost to ' if not win else 'Last appearance — Defeated '))+label(op)+score
    for (year,abbr),games in groups.items():
        games.sort(key=lambda g:int(g['DayNum']));participants={g[k] for g in games for k in ['WTeamID','LTeamID']};losers={g['LTeamID'] for g in games};unbeaten=participants-losers;complete=len(unbeaten)==1 and len(games)==len(participants)-1
        champion=next(iter(unbeaten)) if complete else None
        final=games[-1]
        # Distance through the winner's remaining elimination path identifies finals/semifinals without counting game dates.
        def round_name(g):
            winner=g['WTeamID'];day=int(g['DayNum']);depth=1
            while True:
                nxt=next((x for x in games if int(x['DayNum'])>day and winner in [x['WTeamID'],x['LTeamID']]),None)
                if not nxt:break
                winner=nxt['WTeamID'];day=int(nxt['DayNum']);depth+=1
            return {1:'Final',2:'Semifinals',3:'Quarterfinals'}.get(depth,'Earlier Round') if complete else None
        for tid in participants:
            if tid not in ids:continue
            played=[g for g in games if tid in [g['WTeamID'],g['LTeamID']]];g=played[-1];g={**g,**scores.get((year,g['DayNum'],g['WTeamID'],g['LTeamID']),{})}
            prev=conf['seasons'].setdefault(year,{}).get(ids[tid],{});title=abbr.upper()+' Tournament · '
            text=game_result(g,tid,champ=tid==champion,prefix=title,rd=round_name(g))
            if year=='2020' and not complete:text='Tournament interrupted/canceled (COVID-19) — '+text
            conf['seasons'][year][ids[tid]]={**prev,'result':text,'source':SRC,'tournament_complete':complete,'champion':tid==champion}
    for year in map(str,range(2016,2026)):
        entries=conf['seasons'].setdefault(year,{})
        participants={tid for (y,c),gs in groups.items() if y==year for g in gs for tid in [g['WTeamID'],g['LTeamID']]}
        for slug in teams:
            prev=entries.get(slug,{})
            tid=next((tid for tid,s in ids.items() if s==slug),None);abbr=membership[year].get(tid)
            if tid in participants:continue
            if not abbr:text='Not a Division I member in this season'
            elif abbr=='ivy' and int(year)<=2016:text='No conference tournament held (Ivy League)'
            elif year=='2020':text='Conference tournament canceled (COVID-19)'
            elif abbr in ('ind','independent'):text='Independent — no conference tournament'
            else:text='Did not participate in conference tournament'
            entries[slug]={**prev,'result':text,'source':SRC}
    for y in map(str,range(2016,2026)):national['seasons'][y]={}
    # NCAA bracket ancestry supplies actual game rounds, including First Four slots.
    seeds=defaultdict(dict);slots=defaultdict(dict)
    for r in read('MNCAATourneySeeds'):seeds[r['Season']][r['Seed']]=r['TeamID']
    for r in read('MNCAATourneySlots'):slots[r['Season']][r['Slot']]=(r['StrongSeed'],r['WeakSeed'])
    def round_of(year,g):
        def leaves(slot):
            if slot in seeds[year]:return {seeds[year][slot]}
            if slot not in slots[year]:return set()
            a,b=slots[year][slot];return leaves(a)|leaves(b)
        candidates=[int(s[1]) if s.startswith('R') else 0 for s in slots[year] if {g['WTeamID'],g['LTeamID']}<=leaves(s)]
        return min(candidates) if candidates else None
    ncaa=defaultdict(list)
    for r in read('MNCAATourneyCompactResults'):
        if 2016<=int(r['Season'])<=2025:ncaa[r['Season']].append(r)
    all_secondary=defaultdict(list)
    for r in read('MSecondaryTourneyCompactResults'):
        if 2016<=int(r['Season'])<=2025:all_secondary[r['Season'],r['SecondaryTourney']].append(r)
    for year,games in ncaa.items():
        for tid in {t for g in games for t in [g['WTeamID'],g['LTeamID']]}:
            if tid not in ids:continue
            played=sorted([g for g in games if tid in [g['WTeamID'],g['LTeamID']]],key=lambda g:int(g['DayNum']));g=played[-1];rd=round_of(year,g);champ=rd==6 and tid==g['WTeamID'];seed=next((int(s[1:3]) for s,t in seeds[year].items() if t==tid),None)
            roundlabel={0:'First Four',1:'Round of 64',2:'Round of 32',3:'Sweet 16',4:'Elite Eight',5:'Final Four',6:'National Championship'}.get(rd)
            national['seasons'].setdefault(year,{})[ids[tid]]={'result':game_result(g,tid,champ=champ,prefix=(f'#{seed} Seed · NCAA Tournament · ' if seed else 'NCAA Tournament · '),rd=roundlabel),'tournament':'NCAA','seed':seed,'round':roundlabel,'postseason_games':len(played),'wins':sum(x['WTeamID']==tid for x in played),'source':SRC}
    # 2021 VCU/Oregon was a no-contest; VCU remains a tournament participant.
    for year,seedmap in seeds.items():
        if not 2016<=int(year)<=2025:continue
        participants={tid for g in ncaa.get(year,[]) for tid in [g['WTeamID'],g['LTeamID']]}
        for tid in set(seedmap.values())-participants:
            if tid in ids:national['seasons'].setdefault(year,{})[ids[tid]]={'result':'NCAA Tournament · No contest (COVID-19 protocols)','tournament':'NCAA','source':SRC}
    for (year,tourney),games in all_secondary.items():
        games.sort(key=lambda g:int(g['DayNum']));champion=games[-1]['WTeamID']
        for tid in {t for g in games for t in [g['WTeamID'],g['LTeamID']]}:
            if tid not in ids:continue
            played=[g for g in games if tid in [g['WTeamID'],g['LTeamID']]];g=played[-1]
            national['seasons'].setdefault(year,{})[ids[tid]]={'result':game_result(g,tid,champ=tid==champion,prefix=tourney+' Tournament · '),'tournament':tourney,'postseason_games':len(played),'source':SRC}
    for year in map(str,range(2016,2026)):
        for slug in teams:
            if year=='2020':national['seasons'].setdefault(year,{})[slug]={'result':'Postseason tournaments canceled (COVID-19)','tournament':'canceled','source':SRC}
            elif not national['seasons'].setdefault(year,{}).get(slug) or national['seasons'][year][slug].get('tournament')=='unverified':
                national['seasons'][year][slug]={'result':'No NCAA / NIT / secondary postseason tournament appearance','tournament':'none','source':SRC}
    if args.fetch_2026:enrich_espn_2026(conf,national,teams)
    save(ROOT/'data/cbb/conference-tournament-results.json',conf);save(ROOT/'data/cbb/tournament-results.json',national)
    print('Conference finalized:',{y:sum(bool(v.get('result')) for v in s.values()) for y,s in conf['seasons'].items()})
    print('National unresolved:',{y:sum(v.get('tournament')=='unverified' for v in s.values()) for y,s in national['seasons'].items()})

def enrich_espn_2026(conf,national,teams):
    """Read explicit event notes and final scores; never infer a round from games played."""
    byid={str(t['espn_id']):s for s,t in teams.items()};events={}
    # Query by week so ESPN cannot silently truncate the 1,000-event result set.
    from datetime import date,timedelta
    day=date(2026,3,1)
    while day<date(2026,4,15):
        end=min(day+timedelta(days=6),date(2026,4,15));url='https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?groups=50&limit=1000&dates='+day.strftime('%Y%m%d')+'-'+end.strftime('%Y%m%d')
        with urllib.request.urlopen(url,timeout=45) as r:payload=json.load(r)
        for e in payload.get('events',[]):events[e['id']]=e
        day=end+timedelta(days=1)
    assert len(events)>500, f'Incomplete 2026 scoreboard: {len(events)} events'
    classified=defaultdict(list)
    for e in events.values():
        for c in e.get('competitions',[]):
            if not c.get('status',{}).get('type',{}).get('completed'):continue
            notes=' · '.join(n.get('headline','') for n in c.get('notes',[]));sides=c.get('competitors',[])
            if len(sides)!=2:continue
            is_ncaa=bool(re.search(r'NCAA|Men.s Basketball Championship',notes,re.I))
            is_conf=bool(re.search(r'Championship|Tournament',notes,re.I)) and not is_ncaa and not re.search(r'National Invitation|\bNIT\b|College Basketball|\bCBI\b|Crown|\bCIT\b',notes,re.I)
            tourney='NCAA' if is_ncaa else 'NIT' if re.search(r'National Invitation|\bNIT\b',notes,re.I) else 'Crown' if re.search('Crown',notes,re.I) else 'CBI' if re.search(r'College Basketball Invitational|\bCBI\b',notes,re.I) else 'CIT' if re.search(r'CollegeInsider|\bCIT\b',notes,re.I) else None
            if not (is_conf or tourney):continue
            for side in sides:
                slug=byid.get(side['team']['id']);opp=next(x for x in sides if x is not side)
                if not slug:continue
                won=side.get('winner',False);champ=won and bool(re.search(r'(?:Championship|Tournament|\bNIT\b|Crown)\s*[-–·:]\s*(?:Final|National Championship|Championship)$',notes,re.I))
                # "Final Four" must never be treated as a championship final.
                if re.search('Final Four',notes,re.I):champ=False
                suffix='Champion — Defeated ' if champ else 'Advanced — Defeated ' if won else 'Eliminated — Lost to '
                result=notes+' · '+suffix+opp['team'].get('shortDisplayName',opp['team']['displayName'])+', '+str(side['score'])+'–'+str(opp['score'])
                classified['conference' if is_conf else 'national',slug].append((e['date'],{'result':result,'tournament':tourney or 'conference','champion':champ,'source':url.rsplit('?',1)[0]+'?dates='+e['date'][:10].replace('-',''),'event_id':e['id']}))
    for (kind,slug),rows in classified.items():
        dest=conf if kind=='conference' else national;prev=dest['seasons'].setdefault('2026',{}).get(slug,{})
        dest['seasons']['2026'][slug]={**prev,**max(rows,key=lambda r:r[0])[1]}
    assert sum(k[0]=='conference' for k in classified)>280, 'Incomplete conference tournament field'
    assert sum(k[0]=='national' and max(v,key=lambda r:r[0])[1]['tournament']=='NCAA' for k,v in classified.items())==68, 'Expected 68 NCAA teams'
    for slug in teams:
        for kind,dest in [('conference',conf),('national',national)]:
            if (kind,slug) in classified:continue
            prev=dest['seasons'].setdefault('2026',{}).get(slug,{})
            text='Did not participate in conference tournament' if kind=='conference' else 'No NCAA / NIT / secondary postseason tournament appearance'
            dest['seasons']['2026'][slug]={**prev,'result':text,'tournament':'none','source':'https://www.espn.com/mens-college-basketball/scoreboard/_/date/20260301'}
    print('2026 ESPN events',len(events),'team finishes',len(classified))
if __name__=='__main__':main()
