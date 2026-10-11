#!/usr/bin/env python3
"""Publish official MLB draft records as small team/year files, 2020–2026.
Failure of one season does not invalidate independently verified seasons.
"""
import json,urllib.request,time,datetime,pathlib,argparse,traceback
ROOT=pathlib.Path(__file__).resolve().parent
TEAM_IDS={108:'los-angeles-angels',109:'arizona-diamondbacks',110:'baltimore-orioles',111:'boston-red-sox',112:'chicago-cubs',113:'cincinnati-reds',114:'cleveland-guardians',115:'colorado-rockies',116:'detroit-tigers',117:'houston-astros',118:'kansas-city-royals',119:'los-angeles-dodgers',120:'washington-nationals',121:'new-york-mets',133:'athletics',134:'pittsburgh-pirates',135:'san-diego-padres',136:'seattle-mariners',137:'san-francisco-giants',138:'st-louis-cardinals',139:'tampa-bay-rays',140:'texas-rangers',141:'toronto-blue-jays',142:'minnesota-twins',143:'philadelphia-phillies',144:'atlanta-braves',145:'chicago-white-sox',146:'miami-marlins',147:'new-york-yankees',158:'milwaukee-brewers'}
def collect(year):
    url=f'https://statsapi.mlb.com/api/v1/draft/{year}?limit=1500'
    request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(request,timeout=90) as response:raw=json.load(response)
    groups=raw['drafts']['rounds']
    selected={v:[] for v in TEAM_IDS.values()}
    errors=[];overall_seen=set()
    for group in groups:
        for pick in group.get('picks',[]):
            if pick.get('isPass') is True:continue
            person=pick.get('person') or {}
            name=person.get('fullName') or pick.get('name')
            team_id=(pick.get('team') or {}).get('id')
            number=pick.get('pickNumber')
            if not name or team_id not in TEAM_IDS or number is None:
                errors.append({'round':group.get('round'),'team_id':team_id,'name':name,'pick':number})
                continue
            number=int(number)
            if number in overall_seen:raise ValueError(f'Duplicate overall pick {number}')
            overall_seen.add(number)
            position=pick.get('position') or person.get('primaryPosition') or {}
            school=pick.get('school') or {}
            selected[TEAM_IDS[team_id]].append({
                'round':str(pick.get('pickRound') or group.get('round')),
                'overall_pick':number,'round_pick':pick.get('roundPickNumber'),
                'player':name,
                'position':position.get('abbreviation') if isinstance(position,dict) else position,
                'school':school.get('name') if isinstance(school,dict) else school,
                'player_id':person.get('id'),
                'signed':pick.get('isSigned') if isinstance(pick.get('isSigned'),bool) else None})
    count=sum(map(len,selected.values()))
    minimum=130 if year==2020 else 580
    if errors or count<minimum or any(not x for x in selected.values()):
        raise ValueError(f'{year}: {count} picks; {len(errors)} missing fields; sample {errors[:4]}')
    for rows in selected.values():rows.sort(key=lambda item:item['overall_pick'])
    return selected,count,len(groups),url
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--years',nargs='+',type=int,default=list(range(2020,2027)))
    a=p.parse_args()
    status={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seasons':{}}
    for year in a.years:
        try:
            teams,count,groups,url=collect(year)
            for slug,entries in teams.items():
                dest=ROOT/f'data/mlb/drafts/{year}/{slug}.json'
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text(json.dumps({'year':year,'team':slug,'picks':entries,'source':url},ensure_ascii=False,separators=(',',':'))+'\n')
            status['seasons'][str(year)]={'status':'published','team_count':len(teams),'pick_count':count,'round_groups':groups,'source_url':url}
            print(year,'published',count,'picks',flush=True)
        except Exception as exc:
            status['seasons'][str(year)]={'status':'failed','error':repr(exc)}
            print(year,'FAILED',exc,flush=True)
    dest=ROOT/'data/mlb/draft-publish-status.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(status,indent=2)+'\n')
    if not any(x['status']=='published' for x in status['seasons'].values()):
        raise RuntimeError('No draft season validated')
if __name__=='__main__':main()
