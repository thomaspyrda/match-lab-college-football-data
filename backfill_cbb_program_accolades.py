"""Extract NCAA record-book honors. Requires pdftotext output, not hand-entered awards.
Inputs: Awards-raw.txt, Awards.txt, MFFBook.txt in --source-dir.
"""
import argparse,json,re,unicodedata
from collections import defaultdict,Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
AWARDS='https://s3.amazonaws.com/fs.ncaa.org/Docs/stats/m_basketball_RB/Awards.pdf'
BOOK='https://s3.amazonaws.com/fs.ncaa.org/Docs/stats/m_final4/MFFBook.pdf'
def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower().replace('saint','st').replace('state','st'))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-dir',type=Path,required=True);args=ap.parse_args();src=args.source_dir
    teams=[t for t in json.loads((ROOT/'data/sports/team-registry.json').read_text())['teams'] if t['sport']=='cbb'];names=defaultdict(set)
    for t in teams:
        for name in [t['short_name'],t['name'],*t.get('aliases',[])]:
            if name:names[norm(name)].add(t['slug'])
    for v in json.loads((ROOT/'data/cbb/tournament-team-map.json').read_text())['teams'].values():
        if v.get('slug'):names[norm(v['name'])].add(v['slug'])
    manual={'Pittsburgh':'pittsburgh-panthers','North Carolina St.':'nc-state-wolfpack','Seattle':'seattle-u-redhawks','La.-Lafayette':'louisiana-ragin-cajuns','Cal St. Fullerton':'cal-state-fullerton-titans','LMU (CA)':'loyola-marymount-lions','East Tenn. St.':'east-tennessee-state-buccaneers','Penn':'pennsylvania-quakers','Seattle U.':'seattle-u-redhawks','Fla. Atlantic':'florida-atlantic-owls','Miami (FL)':'miami-hurricanes','Western Ky.':'western-kentucky-hilltoppers','Southern California':'usc-trojans','St. John’s (NY)':'st-johns-red-storm','St. John’s':'st-johns-red-storm','Loyola Chicago':'loyola-chicago-ramblers','Saint Mary’s (CA)':'saint-marys-gaels','Long Island':'long-island-university-sharks','Massachusetts':'massachusetts-minutemen','California':'california-golden-bears'}
    slugs={t['slug'] for t in teams}
    for name,slug in manual.items():
        if slug in slugs:names[norm(name)]={slug}
    def resolve(v):
        values=names.get(norm(v),set());return next(iter(values)) if len(values)==1 else None
    programs={s:{} for s in slugs};seasons=defaultdict(dict);unmapped=Counter();counts=Counter()
    def add(slug,category,year,recipient=None):
        item={'year':int(year)}
        if recipient:item['recipient']=recipient
        rows=programs[slug].setdefault(category,[])
        if item not in rows:rows.append(item);counts[category]+=1
    # Columns are explicitly separated in the official championship-results table.
    text=(src/'MFFBook.txt').read_text();chunk=text[text.index('CHAMPIONSHIP RESULTS'):text.index('FINAL FOUR GAME RECORDS')]
    years=set()
    for line in chunk.splitlines():
        cells=re.split(r'\s{2,}',line.strip())
        if len(cells)<6 or not re.fullmatch(r'(?:19|20)\d{2}',cells[0]) or not re.fullmatch(r'\d+[-–]\d+',cells[2]):continue
        year=int(cells[0]);years.add(year)
        for index,name in enumerate([cells[1],*cells[3:6]]):
            slug=resolve(name.strip('*†+‡'))
            if not slug:unmapped['Final Four: '+name]+=1;continue
            vacated='*' in name
            add(slug,'Vacated Final Four appearances' if vacated else 'NCAA Final Four appearances',year)
            if index==0:add(slug,'Vacated NCAA championships' if vacated else 'NCAA championships',year)
            if index==1:add(slug,'Vacated NCAA runner-up finishes' if vacated else 'NCAA runner-up finishes',year)
    assert len(years)==87 and max(years)==2026, len(years) # 1939–2026 except canceled 2020.
    # Read PDF content order so the three-column All-America section is sequential.
    raw=(src/'Awards-raw.txt').read_text();aa=raw[raw.index('BY SEASON'):raw.index('CONSENSUS\nFIRST-')];year=None;tier='first_team'
    for line in aa.splitlines():
        line=line.strip().replace('\x07','').replace('\u00ad','')
        if re.fullmatch(r'(?:19|20)\d{2}',line):year=int(line);tier='first_team';continue
        if line=='First Team':tier='first_team';continue
        if line=='Second Team':tier='second_team';continue
        if year is None or ',' not in line or line.startswith('Division I'):continue
        parts=[x.strip() for x in line.split(',')]
        # Player name ends before the school field, which must match a known school exactly.
        found=None
        for i in range(1,min(len(parts),4)):
            slug=resolve(parts[i])
            if slug:found=(slug,', '.join(x for x in parts[:i] if x));break
        if not found:
            if re.search(r',\s*\d+-\d+',line):unmapped['All-America: '+line]+=1
            continue
        slug,recipient=found;category='Consensus All-America First Team' if tier=='first_team' else 'Consensus All-America Second Team'
        add(slug,category,year,recipient)
        if year>=2016:
            a=seasons[str(year)].setdefault(slug,{});arr=a.setdefault(tier,[])
            if recipient not in arr:arr.append(recipient)
    # Major player-of-year table has stable fixed-width columns; preserve blank cells.
    lines=(src/'Awards.txt').read_text().splitlines();categories=['Basketball Times Player of the Year','AP Player of the Year','Oscar Robertson Trophy','Wooden Award','NABC Player of the Year','Naismith Player of the Year','Adolph Rupp Trophy']
    for i,line in enumerate(lines):
        match=re.match(r'^(19\d{2}|20\d{2})\s{3,}',line)
        if not match:continue
        year=int(match[1])
        if not 1950<=year<=2026:continue
        # This table starts x=11 with columns spaced 21 chars through 2023;
        # PDF page 19 uses starts 27,48,69,90,111 for the five active series.
        if i<1520 or i>1690:continue
        starts=([11,28,49,70,91,112,133] if year<=1989 else [11,32,53,74,95,116,137]) if year<=2023 else [None,27,48,69,90,111,None]
        nxt=lines[i+1] if i+1<len(lines) else ''
        active=[(j,start) for j,start in enumerate(starts) if start is not None]
        for pos,(j,start) in enumerate(active):
            end=active[pos+1][1] if pos+1<len(active) else len(line)
            chunks=[(m.start(),m.group().strip()) for m in re.finditer(r'\S(?:.*?\S)?(?=\s{2,}|$)',line)];cells=[v for pos,v in chunks if abs(pos-start)<10 and not v.isdigit()];cell=cells[0] if cells else '';schoolchunks=[(m.start(),m.group().strip()) for m in re.finditer(r'\S(?:.*?\S)?(?=\s{2,}|$)',nxt)];schools=[v for pos,v in schoolchunks if abs(pos-start)<10];school=(schools[0] if schools else '').strip(';')
            if not cell:continue
            if ',' in cell:recipient,school=cell.rsplit(',',1);recipient=recipient.strip();school=school.strip()
            else:recipient=cell
            slug=resolve(school)
            if not slug:unmapped['POY: '+str(year)+' '+cell+' / '+school]+=1;continue
            add(slug,categories[j],year,recipient)
            a=seasons[str(year)].setdefault(slug,{});a.setdefault('awards',[]).append({'award':categories[j],'recipient':recipient})
    # Conference title histories use the verified archived seasons only; label the range.
    conf=json.loads((ROOT/'data/cbb/conference-tournament-results.json').read_text())
    for year,entries in conf['seasons'].items():
        if not 2016<=int(year)<=2026:continue
        for slug,r in entries.items():
            if slug not in programs:continue
            if r.get('regular_season_standings',{}).get('championship'):add(slug,'Regular-season conference titles (2015–16 onward)',year)
            if r.get('champion') or re.search(r'Tournament Champion',r.get('result',''),re.I):add(slug,'Conference tournament titles (2015–16 onward)',year)
    # Consistent ordering and source metadata for every program.
    order=['NCAA championships','NCAA runner-up finishes','NCAA Final Four appearances','Regular-season conference titles (2015–16 onward)','Conference tournament titles (2015–16 onward)','Consensus All-America First Team','Consensus All-America Second Team',*categories,'Vacated NCAA championships','Vacated NCAA runner-up finishes','Vacated Final Four appearances']
    programs={s:{k:sorted(groups[k],key=lambda v:(-v['year'],v.get('recipient',''))) for k in order if k in groups} for s,groups in programs.items()}
    out={'sources':[BOOK,AWARDS],'coverage':{'NCAA team honors':'1939–2026, vacated results separated','Consensus All-America':'NCAA consensus selections by season, 1905–2026','major_player_awards':'1950–2026; each series begins when established','conference_titles':'2015–16 through 2025–26'},'programs':programs,'seasons':seasons}
    (ROOT/'data/cbb/national-awards.json').write_text(json.dumps(out,separators=(',',':'),ensure_ascii=False)+'\n')
    report={'honors':dict(counts),'unmapped':dict(unmapped),'programs_with_honors':sum(bool(x) for x in programs.values())};(ROOT/'data/cbb/accolades-backfill-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
