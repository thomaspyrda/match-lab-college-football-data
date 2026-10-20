import json,collections,pathlib,urllib.request
from openpyxl import load_workbook
P=pathlib.Path("data/mlb/game-results/2026.json")
SOURCE="https://shanemcd.org/wp-content/uploads/2026/03/mlb-2026-odds.xlsx"
NAMES=["Arizona Diamondbacks","Athletics","Atlanta Braves","Baltimore Orioles","Boston Red Sox","Chicago Cubs","Chicago White Sox","Cincinnati Reds","Cleveland Guardians","Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals","Los Angeles Angels","Los Angeles Dodgers","Miami Marlins","Milwaukee Brewers","Minnesota Twins","New York Mets","New York Yankees","Philadelphia Phillies","Pittsburgh Pirates","San Diego Padres","San Francisco Giants","Seattle Mariners","St. Louis Cardinals","Tampa Bay Rays","Texas Rangers","Toronto Blue Jays","Washington Nationals"]
SLUGS=["arizona-diamondbacks","athletics","atlanta-braves","baltimore-orioles","boston-red-sox","chicago-cubs","chicago-white-sox","cincinnati-reds","cleveland-guardians","colorado-rockies","detroit-tigers","houston-astros","kansas-city-royals","los-angeles-angels","los-angeles-dodgers","miami-marlins","milwaukee-brewers","minnesota-twins","new-york-mets","new-york-yankees","philadelphia-phillies","pittsburgh-pirates","san-diego-padres","san-francisco-giants","seattle-mariners","st-louis-cardinals","tampa-bay-rays","texas-rangers","toronto-blue-jays","washington-nationals"]
TEAMS=dict(zip(NAMES,SLUGS))
def number(v):
 try:return int(str(v).replace("+",""))
 except:return None
data=json.loads(P.read_text());byid=collections.defaultdict(list)
for team,obj in data["teams"].items():
 for g in obj["games"]:byid[g["game_id"]].append((team,g))
keys=collections.defaultdict(list)
for ident,rows in byid.items():
 if len(rows)!=2:continue
 home=next(((t,g) for t,g in rows if g["location"]=="Home"),None)
 away=next(((t,g) for t,g in rows if g["location"]=="Away"),None)
 if home and away and isinstance(home[1].get("runs_for"),int) and isinstance(away[1].get("runs_for"),int):keys[(home[1]["date"],away[0],home[0],away[1]["runs_for"],home[1]["runs_for"])].append(rows)
import csv
sources=[pathlib.Path(f"data/mlb/sources/2026-odds-upload-part{i}.csv") for i in (1,2,3)]
records=[]
for source in sources:
 with source.open(newline="") as inp:
  records.extend(csv.DictReader(inp,fieldnames=["index","Date","Start Time (EDT)","Away","Away Score","Home","Home Score","Status","Away Starter","Home Starter","O/U","Over","Under","Away ML","Home ML","Home RL Spread","RL Away","RL Home"]))
assert len(records)==2428,len(records)
counts=collections.Counter()
for row in records:
 get=lambda k:row[k]
 if get("Status")!="Final":continue
 away=TEAMS.get(get("Away"));home=TEAMS.get(get("Home"))
 if away is None or home is None:counts["team_unmapped"]+=1;continue
 try:key=(str(get("Date"))[:10],away,home,int(get("Away Score")),int(get("Home Score")))
 except (ValueError,TypeError):continue
 matches=keys.get(key,[])
 if len(matches)!=1:counts["unmatched"]+=1;continue
 spread=get("Home RL Spread")
 try:spread=float(spread)
 except (ValueError,TypeError):spread=None
 try:total=float(get("O/U"))
 except (ValueError,TypeError):total=None
 for team,g in matches[0]:
  ish=team==home
  g["market_starter"]=str((get("Home Starter") if ish else get("Away Starter")) or "")
  g["market_opponent_starter"]=str((get("Away Starter") if ish else get("Home Starter")) or "")
  g["market_moneyline"]=number(get("Home ML") if ish else get("Away ML"))
  g["market_runline_odds"]=number(get("RL Home") if ish else get("RL Away"))
  g["market_ou_total"]=total
  g["market_over_odds"]=number(get("Over"))
  g["market_under_odds"]=number(get("Under"))
  g["market_source"]="shanemcd_2026_consensus"
  if spread not in (-1.5,1.5):
   a=number(get("Away ML"));h=number(get("Home ML"))
   if a is not None and h is not None and a!=h:
    spread=-1.5 if h<a else 1.5
    counts["moneyline_fallback"]+=1 if ish else 0
 if spread in (-1.5,1.5):
   side=spread if ish else -spread
   g["team_runline_side"]=side
   g["team_runline_result"]="W" if g["runs_for"]+side>g["runs_against"] else "L"
   g["runline_source"]="shanemcd_2026_consensus" if get("Home RL Spread") not in ("",None) else "shanemcd_2026_moneyline_fallback"
  if total is not None:
   combined=g["runs_for"]+g["runs_against"]
   g["market_ou_result"]="O" if combined>total else "U" if combined<total else "P"
 counts["matched"]+=1
 if spread in (-1.5,1.5):counts["runline"]+=1
 if total is not None:counts["total"]+=1
P.write_text(json.dumps(data,separators=(",",":"))+"\n")
print(dict(counts))
assert counts["matched"]>=2200
