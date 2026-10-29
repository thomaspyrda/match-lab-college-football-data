"""Recover full-game paint only when every official half/OT is accounted for.

Some historical SIDEARM imports have zero/default full-game paint while keeping
the original period totals. Every period's scoring arithmetic and final sum must
agree before its paint total can contribute to a season.
"""
import re,json
from datetime import datetime
from backfill_cbb_official_paint import ref

def parse_periods(s):
    m=re.search(r'<script\b[^>]*\bid=["\']__NUXT_DATA__["\'][^>]*>(.*?)</script>',s,re.S)
    if not m:return None
    try:d=json.loads(m[1])
    except (ValueError,TypeError):return None
    if not isinstance(d,list):return None
    for b in d:
        if not isinstance(b,dict) or not all(k in b for k in ['homeTeam','visitingTeam','gameDate','homeTeamScore','visitingTeamScore']):continue
        if ref(d,b.get('itsWomens')) is not False:continue
        try:
            periods=[str(ref(d,x)) for x in ref(d,b['periods'])]
            if len(periods)<2 or periods!=[str(i+1) for i in range(len(periods))]:continue
            scores=[int(ref(d,b[k])) for k in ['homeTeamScore','visitingTeamScore']]
            paints=[]
            for side,score,scorekey in zip(['homeTeam','visitingTeam'],scores,['periodScoresHome','periodScoresAway']):
                team=ref(d,b[side]);tot=ref(d,team['totals'])
                specials=ref(d,tot['periodSpecialStats']);stats=ref(d,tot['periodStats'])
                points=[int(ref(d,x)) for x in ref(d,b[scorekey])]
                if not len(specials)==len(stats)==len(points)==len(periods) or sum(points)!=score:raise ValueError('incomplete periods')
                values=[]
                for sp,st,pts in zip(specials,stats,points):
                    sp=ref(d,sp);st=ref(d,st)
                    paint=int(ref(d,sp['pointsInThePaint']));fg=int(ref(d,st['totalFieldGoalsMade']));three=int(ref(d,st['threePointFieldGoalsMade']));ft=int(ref(d,st['freeThrowsMade']))
                    if 2*fg+three+ft!=pts or not 0<=three<=fg or ft<0 or not 0<=paint<=2*(fg-three) or paint%2:raise ValueError('period mismatch')
                    values.append(paint)
                total=sum(values)
                full=ref(d,ref(d,tot['special']).get('pointsInThePaint'))
                if full not in [None,'',0,'0'] and int(full)!=total:raise ValueError('conflicting full-game total')
                paints.append(total)
            if sum(paints)==0:continue
            stamp=str(ref(d,b['gameDate'])).split(' ')[0];day=None
            for fmt in ['%m/%d/%y','%m/%d/%Y','%Y-%m-%d']:
                try:day=datetime.strptime(stamp,fmt).date().isoformat();break
                except ValueError:pass
            home=ref(d,b.get('thisTeamIsHomeTeam'))
            if not day or home is not True and home is not False:continue
            i=0 if home else 1
            return {'date':day,'points':scores[i],'opponent_points':scores[1-i],'paint_for':paints[i],'paint_against':paints[1-i],'format':'Official complete half/OT paint sum; every period scoring arithmetic and final score verified'}
        except (KeyError,ValueError,TypeError,IndexError):continue
    return None

if __name__=='__main__':
    import backfill_cbb_official_paint_legacy_batch as batch
    from backfill_cbb_sidearm_html_paint import parse_html
    original=batch.classic
    batch.classic=lambda body,school,team: parse_periods(body) or parse_html(body,school,team) or original(body,school,team)
    batch.main()
