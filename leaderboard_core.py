"""Top-ten football totals, per-appearance averages, and qualified rates."""
import math
from html import escape
TOTALS=[('Passing Yards','passing_yards'),('Passing TDs','passing_tds'),('Completions','completions'),('Pass Attempts','attempts'),('Rushing Yards','rushing_yards'),('Rushing TDs','rushing_tds'),('Rush Attempts','carries'),('Receiving Yards','receiving_yards'),('Receiving TDs','receiving_tds'),('Receptions','receptions'),('Targets','targets'),('Scrimmage Yards','scrimmage_yards'),('Scrimmage TDs','scrimmage_tds'),('Combined Tackles','combined_tackles'),('Solo Tackles','solo_tackles'),('Sacks','sacks'),('Tackles for Loss','tfl'),('QB Hits / Hurries','qb_hits'),('Defensive INTs','def_interceptions'),('Passes Defended','passes_defended'),('Forced Fumbles','forced_fumbles'),('Field Goals Made','fg_made'),('Kicking Points','kicking_points'),('Punt Return Yards','punt_return_yards'),('Kickoff Return Yards','kick_return_yards')]
AVERAGES=[(label+' / Game',key) for label,key in TOTALS if key in ['passing_yards','passing_tds','rushing_yards','rushing_tds','receiving_yards','receiving_tds','receptions','scrimmage_yards','combined_tackles','sacks','tfl','qb_hits','passes_defended']]
RATES=[('Completion %','completion_pct','attempts',14),('Passer Rating','passer_rating','attempts',14),('Passing Yards / Attempt','passing_ypa','attempts',14),('Rushing Yards / Carry','yards_per_carry','carries',6),('Receiving Yards / Catch','yards_per_reception','receptions',2),('Field Goal %','fg_pct','fg_att',1),('Punting Average','punt_average','punt_att',2)]
BREAKERS={'passing_yards':['passing_tds','completions'],'passing_tds':['passing_yards','completions'],'rushing_yards':['rushing_tds','carries'],'rushing_tds':['rushing_yards','carries'],'receiving_yards':['receiving_tds','receptions'],'receiving_tds':['receiving_yards','receptions'],'receptions':['receiving_yards','receiving_tds'],'sacks':['qb_hits','tfl','combined_tackles'],'def_interceptions':['passes_defended','defensive_tds','interception_yards','combined_tackles'],'passes_defended':['def_interceptions','combined_tackles']}
def derived(p,college=False):
 t=p['stats'];get=lambda k:t.get(k,0)
 t['scrimmage_yards']=get('rushing_yards')+get('receiving_yards');t['scrimmage_tds']=get('rushing_tds')+get('receiving_tds')
 if get('attempts'):
  n=t['attempts'];t['completion_pct']=100*get('completions')/n;t['passing_ypa']=get('passing_yards')/n
  t['passer_rating']=(8.4*get('passing_yards')+330*get('passing_tds')+100*get('completions')-200*get('interceptions'))/n if college else sum(max(0,min(2.375,v)) for v in [(get('completions')/n-.3)*5,(get('passing_yards')/n-3)*.25,get('passing_tds')/n*20,2.375-get('interceptions')/n*25])/6*100
 for key,top,bottom,scale in [('yards_per_carry','rushing_yards','carries',1),('yards_per_reception','receiving_yards','receptions',1),('fg_pct','fg_made','fg_att',100),('punt_average','punt_yards','punt_att',1)]:
  if get(bottom):t[key]=scale*get(top)/get(bottom)
def categories(players,minimum,college=False):
 out=[];unsupported={'targets','forced_fumbles'} if college else set()
 specs=[(title,key,'totals',None,0) for title,key in TOTALS if key not in unsupported]+[(title,key,'averages',None,0) for title,key in AVERAGES]+[(title,key,'efficiency',den,limit) for title,key,den,limit in RATES]
 for title,key,group,den,limit in specs:
  if college and key=='passer_rating':title='Passing Efficiency'
  if key=='qb_hits':title=title.replace('QB Hits / Hurries','QB Hurries' if college else 'QB Hits')
  eligible=[]
  for p in players:
   t=p['stats'];gp=p['games_played']
   if t.get(key,0)<=0:continue
   if group!='totals' and (gp<minimum or not p.get('gp_verified',True)):continue
   if den and t.get(den,0)<limit*gp:continue
   value=t[key]/gp if group=='averages' else t[key];eligible.append((p,value))
  order=sorted(eligible,key=lambda x:(-x[1],tuple(-x[0]['stats'].get(k,0) for k in BREAKERS.get(key,[den] if den else [])),x[0]['name'],x[0]['id']))
  top=[dict(rank=1+sum(v>value+1e-10 for q,v in eligible),player_id=p['id'],name=p['name'],teams=sorted(p['teams']),games=p['games_played'],value=round(value,6)) for p,value in order[:10]]
  qualification='' if group=='totals' else f'Minimum {minimum} recorded player appearances.'
  if den:qualification+=f' At least {limit} {den.replace("_"," ")} per appearance.'
  out.append(dict(title=title,metric=key,group=group,players=top,qualification=qualification))
 return out
def tables(payload,team_link):
 groups=[]
 for group,label in [('totals','Season Totals'),('averages','Averages per Game'),('efficiency','Efficiency Leaders')]:
  cards=[]
  for c in [x for x in payload['categories'] if x['group']==group]:
   rows=[]
   for r in c['players']:
    teams=' · '.join(team_link(t) for t in r['teams']);value=f'{r["value"]:,.2f}'.rstrip('0').rstrip('.') if group!='totals' or not float(r['value']).is_integer() else f'{int(r["value"]):,}'
    rows.append(f'<tr><td>{r["rank"]}</td><td>{escape(r["name"])}</td><td>{teams}</td><td>{r["games"]}</td><td>{value}</td></tr>')
   cards.append(f'<section class="leaderboard-section"><h3>{c["title"]}</h3><p class="leader-qualification">{escape(c["qualification"])}</p><div class="leaderboard-table-wrap"><table class="data-table"><thead><tr><th>Rank</th><th>Player</th><th>Team</th><th>GP</th><th>{"Avg" if group=="averages" else "Value" if group=="efficiency" else "Total"}</th></tr></thead><tbody>{"".join(rows) or "<tr><td colspan=5>No qualifying players yet.</td></tr>"}</tbody></table></div></section>')
  groups.append(f'<section id="{group}" class="leader-group"><h2>{label}</h2><div class="leaderboard-grid">{"".join(cards)}</div></section>')
 nav='<nav class="leader-group-nav" aria-label="Leader statistic groups"><a href="#totals">Season Totals</a><a href="#averages">Averages / Game</a><a href="#efficiency">Efficiency</a></nav>'
 return nav+''.join(groups)
