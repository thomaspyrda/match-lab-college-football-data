"""Full-game-only parser for official classic SIDEARM HTML basketball boxes."""
import re,html
from datetime import datetime
from backfill_cbb_legacy_paint import norm

def parse_html(s,school,team):
    if not re.search(r'<article\b[^>]*class=["\'][^"\']*\bmbball\b',s,re.I):return None
    start=re.search(r'<section\b[^>]*\bid=["\']box-score["\'][^>]*>',s,re.I)
    if not start:return None
    s=s[start.end():]
    # Only the full-game panel; never read first/second-half or play-by-play tabs.
    end=re.search(r'<section\b[^>]*\bid=["\'](?:\d+-box|play-by-play|play-analysis)["\']',s,re.I)
    if end:s=s[:end.start()]
    date=re.search(r'<dt>\s*Date\s*</dt>\s*<dd>\s*(\d{1,2}/\d{1,2}/\d{2,4})\s*</dd>',s,re.I)
    headings=list(re.finditer(r'<h3\b[^>]*class=["\'][^"\']*sub-heading[^"\']*["\'][^>]*>(.*?)</h3>',s,re.S|re.I))
    if not date or len(headings)!=2:return None
    values=[]
    for i,m in enumerate(headings):
        name=html.unescape(re.sub('<[^>]+>',' ',m[1])).strip()
        n=re.fullmatch(r'(.*?)\s+(\d+)',name)
        if not n:return None
        part=s[m.end():headings[i+1].start() if i==0 else len(s)]
        paint=re.findall(r'Points\s+in\s+the\s+Paint:\s*(\d+)',part,re.I)
        if len(paint)!=1:return None
        values.append((n[1].strip(),int(n[2]),int(paint[0])))
    aliases={norm(x) for x in [school,team['name'],team['short_name'],*team.get('aliases',[])] if x}
    own=[i for i,(n,p,a) in enumerate(values) if norm(n) in aliases or len(norm(n))>=4 and norm(team['name']).startswith(norm(n))]
    if len(own)!=1:return None
    i=own[0];_,p,a=values[i];_,q,b=values[1-i]
    if not 0<=a<=p or not 0<=b<=q or a%2 or b%2 or a+b==0:return None
    stamp=None
    for fmt in ['%m/%d/%y','%m/%d/%Y']:
        try:stamp=datetime.strptime(date[1],fmt).date().isoformat();break
        except ValueError:pass
    if not stamp:return None
    return {'date':stamp,'points':p,'opponent_points':q,'paint_for':a,'paint_against':b,'format':'Official whole-game SIDEARM HTML panel; matched final score'}
