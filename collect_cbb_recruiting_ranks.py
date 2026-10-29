"""Verified incoming recruiting classes; season 2015-16 uses the 2015 class."""
import json
from collections import Counter
from datetime import datetime, timezone
from cbb_verified_source import ROOT, BASE, crosswalk, fetch, finite, save
OUTPUT=ROOT/'data/cbb/recruiting-classes.json'
def main():
    identity=crosswalk()
    existing=json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {'seasons':{}}
    report={'years':{},'unmapped':[]}
    for class_year in range(2015,2027):
        rows=fetch('/recruiting/teams',year=class_year)
        if not isinstance(rows,list):raise ValueError('Unexpected recruiting response')
        target=existing['seasons'].setdefault(str(class_year+1),{})
        count=Counter(source_rows=len(rows))
        for row in rows:
            if row.get('year')!=class_year:raise ValueError('Wrong recruiting class year')
            slug=identity.get(str(row.get('teamId')))
            if not slug:
                report['unmapped'].append({'year':class_year,'team':row.get('team'),'team_id':row.get('teamId')});continue
            rank,points=row.get('ranking'),row.get('rating')
            if not finite(rank) or int(rank)!=rank or not 1<=rank<=500 or not finite(points) or points<0:
                count['invalid']+=1;continue
            # Class-year metadata distinguishes incoming recruits from season ending year.
            entry={'national_rank':int(rank),'points':points,'class_year':class_year,
                'source':BASE+'/recruiting/teams?year='+str(class_year),
                'ranking_system':'CollegeBasketballData composite',
                'source_team_id':row['teamId'],'source_team_name':row['team']}
            if slug not in target:count['added']+=1
            elif target[slug]!=entry:count['corrected']+=1
            target[slug]=entry;count['matched']+=1
        report['years'][str(class_year)]=dict(count);print(class_year,dict(count),flush=True)
    existing.update(source=BASE+'/recruiting/teams',season_mapping='season ending year = incoming class year + 1',updated_at=datetime.now(timezone.utc).isoformat())
    report['total_team_classes']=sum(len(v) for v in existing['seasons'].values())
    if report['total_team_classes']==0:raise ValueError('No recruiting rankings returned; refusing empty success')
    save(OUTPUT,existing);save(ROOT/'data/cbb/recruiting-backfill-report.json',report)
    print('Verified recruiting classes:',report['total_team_classes'])
if __name__=='__main__':main()
