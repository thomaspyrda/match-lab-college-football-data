#!/usr/bin/env python3
"""Build static NBA standings archive from historical RealGM league standings.
Regular season W/L, opponent PPG, home/away splits are extracted by column
headers, validated, and saved as team-season JSON. Never overwrite PPG from
the separate BetWise TeamRankings screenshot archive.
"""
import argparse,json,re,time
from pathlib import Path
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]/"teams"/"data"
ALIASES={
"atlanta hawks":"atlanta-hawks","boston celtics":"boston-celtics",
"brooklyn nets":"brooklyn-nets","charlotte hornets":"charlotte-hornets",
"chicago bulls":"chicago-bulls","cleveland cavaliers":"cleveland-cavaliers",
"dallas mavericks":"dallas-mavericks","denver nuggets":"denver-nuggets",
"detroit pistons":"detroit-pistons","golden state warriors":"golden-state-warriors",
"houston rockets":"houston-rockets","indiana pacers":"indiana-pacers",
"los angeles clippers":"la-clippers","la clippers":"la-clippers",
"los angeles lakers":"los-angeles-lakers","memphis grizzlies":"memphis-grizzlies",
"miami heat":"miami-heat","milwaukee bucks":"milwaukee-bucks",
"minnesota timberwolves":"minnesota-timberwolves",
"new orleans pelicans":"new-orleans-pelicans","new york knicks":"new-york-knicks",
"oklahoma city thunder":"oklahoma-city-thunder","orlando magic":"orlando-magic",
"philadelphia sixers":"philadelphia-76ers","philadelphia 76ers":"philadelphia-76ers",
"phoenix suns":"phoenix-suns","portland trail blazers":"portland-trail-blazers",
"sacramento kings":"sacramento-kings","san antonio spurs":"san-antonio-spurs",
"toronto raptors":"toronto-raptors","utah jazz":"utah-jazz",
"washington wizards":"washington-wizards"}
def clean(s):return re.sub(r"\s+"," ",s.lower().replace("*","")).strip()
def record(s):
 m=re.fullmatch(r"(\d{1,2})-(\d{1,2})",s)
 if not m:raise ValueError("Invalid W-L: "+s)
 return tuple(map(int,m.groups()))
def scrape(session,year):
 url=f"https://basketball.realgm.com/nba/standings/league/{year}"
 response=session.get(url,timeout=45);response.raise_for_status()
 soup=BeautifulSoup(response.text,"html.parser")
 wanted={"Team","W","L","OPPG","Home","Away"}
 for table in soup.select("table"):
  header=[cell.get_text(" ",strip=True) for cell in table.select("thead tr:last-child th, thead tr:last-child td")]
  if not wanted.issubset(set(header)):continue
  cols={c:i for i,c in enumerate(header)}
  teams={}
  for tr in table.select("tbody tr"):
   cells=[cell.get_text(" ",strip=True) for cell in tr.find_all(["td","th"],recursive=False)]
   if len(cells)<len(cols):continue
   def get(k):return cells[cols[k]]
   slug=ALIASES.get(clean(get("Team")))
   if not slug:continue
   w,l=int(get("W")),int(get("L"))
   h,hl=record(get("Home"));a,al=record(get("Away"))
   # Some seasons involve special neutral-site games; preserve them only
   # when paired splits agree or a neutral record is independently sourced.
   home=get("Home") if h+a==w and hl+al==l else None
   away=get("Away") if home else None
   teams[slug]={"record":{"wins":w,"losses":l,"overall":f"{w}-{l}"},
      "metrics":{"points_allowed_per_game":float(get("OPPG"))}}
   if home:teams[slug]["record"].update(home=home,away=away)
  if len(teams)==30:
   if any(not 55 <= t["record"]["wins"]+t["record"]["losses"] <= 83 for t in teams.values()):
    raise ValueError(f"Bad schedule size {year}")
   return {"source":url,"teams":teams,"season_key":str(year)}
 raise ValueError(f"Could not extract complete 30-team RealGM standings for {year}")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--first",type=int,default=2016)
 p.add_argument("--last",type=int,default=2024)
 a=p.parse_args()
 if not(2016<=a.first<=a.last<=2024):raise ValueError("season range")
 path=ROOT/"standings-history.json";data={"seasons":{}}
 if path.exists():data=json.loads(path.read_text())
 s=requests.Session();s.headers["User-Agent"]="Mozilla/5.0 (compatible; BetWiseArchive/1.0)"
 errors={}
 for y in range(a.first,a.last+1):
  try:
   season=scrape(s,y)
   data["seasons"][str(y)]=season
   print(f"{y}: 30/30 teams; PA/G, W-L, home/away",flush=True)
  except Exception as e:
   errors[str(y)]=str(e)
   print(f"{y}: unavailable: {e}",flush=True)
  time.sleep(2)
 ROOT.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,indent=2)+"\n")
 (ROOT/"standings-history-coverage.json").write_text(
   json.dumps({"validated_seasons":sorted(data["seasons"]),"errors":errors},indent=2)+"\n")
 if errors:raise RuntimeError("Historical standings incomplete: "+str(errors))
 print(f"Validated {30*len(data['seasons'])} team-seasons",flush=True)
if __name__=="__main__":main()
