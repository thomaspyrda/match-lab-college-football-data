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
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({"source":"Saved ESPN team-player season archives; rate statistics require >=10 games","seasons":result},separators=(",",":"),ensure_ascii=False)+"\n")
    folder=ROOT/"cbb/division-one-season-leaders"
    folder.mkdir(parents=True,exist_ok=True)
    markup="<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>CBB Division I Season Leaders | BetWise</title><meta name=\"description\" content=\"College basketball Division I season statistical leaders since 2015–16.\"><link rel=\"canonical\" href=\"https://matchlab.parlaycalculator.bet/cbb/division-one-season-leaders/\"><link rel=\"stylesheet\" href=\"/cfb-dashboard-preview/styles.css?v=27\"><link rel=\"stylesheet\" href=\"/site-navigation.css?v=20261021-1\"><link rel=\"stylesheet\" href=\"/nba/rankings/rankings.css?v=mobile-logos-20261021\"><script defer src=\"/site-navigation-v11.js?v=20261027-cbb-rankings\"></script><style>.nba-rankings-main{max-width:1220px;margin:0 auto;padding:28px 20px 65px}.leaderboard-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px}.leader-tile{background:#191e23;border:1px solid #34404b;border-radius:13px;padding:18px}.leader-tile table{width:100%;border-collapse:collapse;font-size:13px}.leader-tile th,.leader-tile td{padding:8px;border-bottom:1px solid #34404b;text-align:left}.leader-tile a{color:#9edaff}.rank-tabs{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0}.rank-tabs a{padding:12px 18px;border:1px solid #414d59;border-radius:9px;color:#fff;text-decoration:none}.rank-tabs a.active{background:#174676;border-color:#4793df}.nba-rank-season-control select{margin-left:12px;padding:9px;background:#141c23;color:#fff;border:1px solid #52606d;border-radius:7px}@media(max-width:500px){.leaderboard-grid{grid-template-columns:1fr}}</style></head><body class=\"nba-rankings-page\"><header class=\"site-header\"><div class=\"header-inner\"><a class=\"betwise-brand\" href=\"https://parlaycalculator.bet/\"><img src=\"/assets/betwise-logo.png\" width=\"60\" height=\"60\" alt=\"BetWise\"></a><nav class=\"site-nav\" aria-label=\"Primary navigation\"></nav><details class=\"mobile-menu\"><summary>Menu</summary><nav aria-label=\"Mobile navigation\"></nav></details></div></header><main class=\"nba-rankings-main\"><p class=\"eyebrow\">BETWISE CBB · SEASON LEADERS</p><h1>Division I Basketball Season Leaders</h1><p class=\"page-intro\">Top players by season totals, averages and shooting statistics, 2015–16 through 2025–26.</p><div class=\"nba-rank-season-control\"><label for=\"year\">Choose season <select id=\"year\"></select></label></div><p class=\"rank-tabs-label\">Explore CBB Rankings</p><nav class=\"rank-tabs\" aria-label=\"CBB Rankings\"><a href=\"/cbb/rankings/\">Team Rankings</a><a href=\"/cbb/division-one-season-leaders/\" class=\"active\" aria-current=\"page\">Season Leaders</a></nav><div id=\"leaders\" class=\"leaderboard-grid\"></div><p class=\"page-intro\">Player data from saved ESPN season archives. Rate statistics require at least ten games; this is an archive coverage rule, not an official NCAA qualification standard.</p></main><footer class=\"research-footer\">BetWise College Basketball · <a href=\"/cbb/teams/\">Browse all teams</a></footer><script src=\"/cbb/division-one-season-leaders/leaders.js\"></script></body></html>"
    (folder/"index.html").write_text(markup)
    js="(async()=>{const data=await fetch('/data/cbb/division-one-season-leaders.json').then(r=>r.json());const sel=document.querySelector('#year');const years=Object.keys(data.seasons).sort().reverse();sel.innerHTML=years.map(y=>'<option value=\"'+y+'\">'+(Number(y)-1)+'–'+y.slice(-2)+'</option>').join('');const esc=x=>String(x??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));function render(){const d=data.seasons[sel.value]||{};document.querySelector('#leaders').innerHTML=Object.values(d).map(cat=>'<section class=\"leader-tile\"><h2>'+esc(cat.label)+'</h2><table><thead><tr><th>#</th><th>Player</th><th>Team</th><th>Value</th></tr></thead><tbody>'+cat.leaders.map((p,i)=>'<tr><td>'+(i+1)+'</td><td><a href=\"/cbb/teams/'+encodeURIComponent(p.team)+'/\">'+esc(p.name)+'</a></td><td>'+esc(p.team.replace(/-/g,' '))+'</td><td>'+esc(p.value)+'</td></tr>').join('')+'</tbody></table></section>').join('')}sel.addEventListener('change',render);render()})().catch(()=>{document.querySelector('#leaders').textContent='Season Leaders data temporarily unavailable.'})"
    (folder/"leaders.js").write_text(js)
    print("D1 season leaders:",team_count,"teams",len(result),"seasons")
if __name__=="__main__":main()
