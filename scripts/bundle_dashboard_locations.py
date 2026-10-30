"""Bundle the shared location panel into existing app assets for atomic deployment."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def bundle(base,sport,filename):
 source=(ROOT/'sports-research/dashboard-locations-v1.js').read_text()
 feed=json.loads((base/'data/location-records.json').read_text())
 feed['teams']={tid:rows for tid,rows in feed['teams'].items() if any(r.get('games') for r in rows.values())}
 source=source.replace('document.currentScript.dataset.sport',json.dumps(sport)).replace('let locationData=null;','let locationData='+json.dumps(feed,separators=(',',':'))+';')
 p=base/filename;s=p.read_text();s=re.sub(r'/\* BEGIN SHARED LOCATION PANEL \*/.*?/\* END SHARED LOCATION PANEL \*/\n','',s,flags=re.S)
 p.write_text('/* BEGIN SHARED LOCATION PANEL */\n'+source+'/* END SHARED LOCATION PANEL */\n'+s)
 p=base/'index.html';s=p.read_text();s=re.sub(r'<script src="https://matchlab.parlaycalculator.bet/sports-research/dashboard-locations-v1.js" data-sport="[^"]+"></script>','',s)
 s=s.replace('<link rel="stylesheet" href="https://matchlab.parlaycalculator.bet/sports-research/dashboard-locations-v1.css">','<style id="by-location-layout">'+(ROOT/'sports-research/dashboard-locations-v1.css').read_text()+'</style>')
 s=s.replace('20261030-by-location-2','20261030-by-location-3');p.write_text(s)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--nfl-dir',type=Path);args=p.parse_args()
 for sport in ['nba','cbb','cfb','mlb']:bundle(ROOT/('cfb-dashboard-preview' if sport=='cfb' else f'{sport}/dashboard'),sport,'app-player-hands-relievers-v3.js' if sport=='mlb' else 'app.js')
 if args.nfl_dir:bundle(args.nfl_dir,'nfl','app.js')
