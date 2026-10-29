"""Small authenticated CBBD reader and exact ESPN-team identity crosswalk."""
import json, math, os, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path
ROOT = Path(__file__).resolve().parent
BASE = 'https://api.collegebasketballdata.com'
def fetch(path, **params):
    key = os.environ.get('CBBD_API_KEY', '').strip()
    if not key: raise RuntimeError('CBBD_API_KEY is required')
    url = BASE + path + ('?' + urllib.parse.urlencode(params) if params else '')
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'Authorization':'Bearer '+key,'User-Agent':'BetWiseArchive/1.0'})
            with urllib.request.urlopen(req, timeout=60) as response: return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt == 2: raise
        except (TimeoutError, OSError):
            if attempt == 2: raise
        time.sleep(2 ** attempt)
def finite(value):
    return isinstance(value, (int,float)) and not isinstance(value,bool) and math.isfinite(value)
def teams():
    return [t for t in json.loads((ROOT/'data/sports/team-registry.json').read_text())['teams'] if t['sport']=='cbb']
def crosswalk():
    own = {str(t['espn_id']): t['slug'] for t in teams()}
    rows = fetch('/teams')
    if not isinstance(rows,list) or len(rows)<300: raise ValueError('Incomplete CBBD team directory')
    result = {str(t['id']):own[str(t.get('sourceId'))] for t in rows if str(t.get('sourceId')) in own}
    if len(result)<300: raise ValueError('Incomplete exact ESPN crosswalk')
    return result
def save(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
