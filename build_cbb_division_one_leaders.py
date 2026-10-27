"""Build Division I CBB season leaders from saved ESPN team-player archives.
Only the requested historical seasons are published; no network dependency.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CATS={"points":"Points","avgPoints":"Points Per Game","rebounds":"Rebounds","avgRebounds":"Rebounds Per Game","assists":"Assists","avgAssists":"Assists Per Game","steals":"Steals","avgSteals":"Steals Per Game","blocks":"Blocks","avgBlocks":"Blocks Per Game","fieldGoalPct":"Field Goal %","threePointFieldGoalPct":"3-Point %","freeThrowPct":"Free Throw %","avgMinutes":"Minutes Per Game"}
RATE={"avgPoints","avgRebounds","avgAssists","avgSteals","avgBlocks","fieldGoalPct","threePointFieldGoalPct","freeThrowPct","avgMinutes"}
def main():
    seasons={}
    team_count=0
    for path in sorted((ROOT/"data/cbb/teams").glob("*.json")):
        data=json.loads(path.read_text());team_count+=1
        for year,season in data.get("seasons",{}).items():
            if not 2016<=int(year)<=2026:continue
            for player in season.get("players",[]):
                stats=player.get("stats") or {}
                if not player.get("name") or not isinstance(stats,dict):continue
                gp=stats.get("gamesPlayed")
                if not isinstance(gp,(int,float)) or gp<1:continue
                row={"name":player["name"],"team":data["slug"],"id":str(player.get("id") or ""),"gp":gp}
                for metric in CATS:
                    value=stats.get(metric)
                    if isinstance(value,(int,float)) and not isinstance(value,bool):
                        # Avoid misleading percentages from players with one appearance.
                        if metric in RATE and gp<10:continue
                        seasons.setdefault(year,{}).setdefault(metric,[]).append(dict(row,value=round(float(value),3)))
    result={}
    for year,categories in seasons.items():
        result[year]={}
        for metric,rows in categories.items():
            rows.sort(key=lambda x:(-x["value"],x["name"],x["team"]))
            result[year][metric]={"label":CATS[metric],"leaders":rows[:10],"eligible":len(rows)}
    output=ROOT/"data/cbb/division-one-season-leaders.json"
    output.write_text(json.dumps({"source":"Saved ESPN team-player season archives; rate statistics require >=10 games","seasons":result},separators=(",",":"),ensure_ascii=False)+"\n")
    folder=ROOT/"cbb/division-one-season-leaders"
    folder.mkdir(parents=True,exist_ok=True)
    markup='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CBB Division I Season Leaders | BetWise Sports</title><style>body{background:#101b25;color:#fff;font:16px system-ui;margin:0}main{max-width:1180px;margin:40px auto;padding:20px}a{color:#78cbff}select{padding:12px;background:#151515;color:white;border:1px solid #555;border-radius:8px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px}.tile{border:1px solid #303f4c;background:#191e23;border-radius:13px;padding:18px}.tile h2{font-size:18px}ol{padding-left:25px}li{padding:7px 0}small{color:#bbb}h1{font-size:34px}</style></head><body><main><p><a href="/cbb/teams/">All CBB Teams</a></p><h1>Division I Men's Basketball Season Leaders</h1><p>Historical top ten leaders from archived ESPN season player totals and averages.</p><label>Season <select id="year"></select></label><div id="leaders" class="grid"></div><p>Rate statistics require at least ten recorded appearances. Data coverage depends on the archived ESPN player feed.</p></main><script src="/cbb/division-one-season-leaders/leaders.js"></script></body></html>'''
    (folder/"index.html").write_text(markup)
    js="""(async()=>{const data=await fetch('/data/cbb/division-one-season-leaders.json').then(r=>r.json());const sel=document.querySelector('#year');const years=Object.keys(data.seasons).sort().reverse();sel.innerHTML=years.map(y=>'<option value="'+y+'">'+(Number(y)-1)+'–'+y.slice(-2)+'</option>').join('');const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));function render(){const d=data.seasons[sel.value]||{};document.querySelector('#leaders').innerHTML=Object.values(d).map(cat=>'<section class="tile"><h2>'+esc(cat.label)+'</h2><ol>'+cat.leaders.map(p=>'<li><a href="/cbb/teams/'+encodeURIComponent(p.team)+'/">'+esc(p.name)+'</a> <small>'+esc(p.team.replace(/-/g,' '))+'</small> <strong>'+esc(p.value)+'</strong></li>').join('')+'</ol></section>').join('')}sel.addEventListener('change',render);render()})().catch(()=>{document.querySelector('#leaders').textContent='Leader data unavailable.'})"""
    (folder/"leaders.js").write_text(js)
    print("D1 season leaders:",team_count,"teams",len(result),"seasons")
if __name__=="__main__":main()
