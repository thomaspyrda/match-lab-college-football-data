#!/usr/bin/env python3
"""Import NBA historical TeamRankings game logs and betting lines.

Collection is strict: each requested dated season must return a table with
matches for that season and non-duplicated games. No current-season fallback.
Separate source file preserves provenance and never overwrites NBA Stats files.
"""
import argparse,json,re,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote
import pandas as pd
import requests

OUT=Path(__file__).resolve().parents[1]/"teams"/"data"
TEAMS={
"atlanta-hawks":"Atlanta","boston-celtics":"Boston","brooklyn-nets":"Brooklyn",
"charlotte-hornets":"Charlotte","chicago-bulls":"Chicago","cleveland-cavaliers":"Cleveland",
"dallas-mavericks":"Dallas","denver-nuggets":"Denver","detroit-pistons":"Detroit",
"golden-state-warriors":"Golden State","houston-rockets":"Houston",
"indiana-pacers":"Indiana","la-clippers":"LA Clippers","los-angeles-lakers":"LA Lakers",
"memphis-grizzlies":"Memphis","miami-heat":"Miami","milwaukee-bucks":"Milwaukee",
"minnesota-timberwolves":"Minnesota","new-orleans-pelicans":"New Orleans",
"new-york-knicks":"New York","oklahoma-city-thunder":"Okla City",
"orlando-magic":"Orlando","philadelphia-76ers":"Philadelphia","phoenix-suns":"Phoenix",
"portland-trail-blazers":"Portland","sacramento-kings":"Sacramento",
"san-antonio-spurs":"San Antonio","toronto-raptors":"Toronto","utah-jazz":"Utah",
"washington-wizards":"Washington"}
ALIASES={re.sub(r"[^a-z0-9]","",n.lower()):slug for slug,n in TEAMS.items()}
ALIASES.update({"lakers":"los-angeles-lakers","clippers":"la-clippers","oklahomacity":"oklahoma-city-thunder"})
def norm(s):return re.sub(r"[^a-z0-9]","",str(s).lower())
def date_end(year):
 if year==2020:return "2020-10-20"
 if year==2021:return "2021-07-25"
 return f"{year}-07-10"
def numeric(s):
 try:return float(str(s).strip().replace("%","").replace(",","").replace("+",""))
 except (ValueError,TypeError):return None
def table_for(html):
 tables=pd.read_html(html)
 for df in tables:
  df.columns=[str(c).strip() for c in df.columns]
  if {"Date","Opponent","Result"}.issubset(df.columns):
   return df
 raise RuntimeError("Game table not found")
def parse(row,year):
 date=str(row["Date"]).strip()
 match=re.search(r"(\d{1,2})/(\d{1,2})",date)
 if not match:return None
 month,day=map(int,match.groups())
 # An NBA season starts the preceding fall. July/August are postseason only.
 calendar_year=year-1 if month>=9 else year
 d=f"{calendar_year}-{month:02d}-{day:02d}"
 raw=str(row["Result"])
 score=re.search(r"([WL])\s*(\d+)\s*[-–]\s*(\d+)",raw,re.I)
 if not score:return None
 opponent=str(row["Opponent"]).replace("at ","").strip()
 opponent_slug=ALIASES.get(norm(opponent))
 if not opponent_slug:raise RuntimeError(f"Unknown opponent {opponent!r}")
 site=str(row.get("Location",row.get("H/A/N",""))).strip()
 if site not in ("Home","Away","Neutral"):raise RuntimeError(f"Location absent: {site!r}")
 points=int(score.group(2));allowed=int(score.group(3))
 if (points>allowed)!=(score.group(1).upper()=="W"):raise RuntimeError("Score/result mismatch")
 spread=numeric(row.get("Spread"))
 total_raw=str(row.get("Total",""))
 total_match=re.search(r"(?:Ov|Un|Over|Under)?\s*(\d+(?:\.\d+)?)",total_raw,re.I)
 total=float(total_match.group(1)) if total_match else None
 ats="—"; ou="—"
 if spread is not None:
  margin=points-allowed+spread
  ats="W" if margin>0 else ("L" if margin<0 else "P")
 if total is not None:
  combined=points+allowed
  ou="O" if combined>total else ("U" if combined<total else "P")
 return {"date":d,"location":site,"opponent_name":opponent,"opponent_slug":opponent_slug,
   "result":score.group(1).upper(),"score_for":points,"score_against":allowed,
   "spread":spread,"total":total,"ats_result":ats,"ou_result":ou,
   "moneyline":numeric(row.get("Money"))}
def gather(session,slug,year):
 date=date_end(year)
 # Historically a dated team overview is used. Reject if its game year does not match.
 url=f"https://www.teamrankings.com/nba/team/{slug}?date={date}"
 response=session.get(url,timeout=45);response.raise_for_status()
 table=table_for(response.text)
 games=[g for _,row in table.iterrows() if (g:=parse(row,year)) is not None]
 games=[g for g in games if int(g["date"][:4]) in (year-1,year)]
 # A complete NBA season normally has at least 60 games. Some include playoffs.
 if not 60<=len(games)<=115:raise RuntimeError(f"Implausible {year} game count {len(games)}")
 # Validate that a late-season row exists for the requested season, rather
 # than accepting a present-day game log returned after an ignored date.
 if max(g["date"] for g in games)[:4] != str(year):
  raise RuntimeError(f"Response does not contain requested season {year}")
 dates=[(g["date"],g["opponent_slug"],g["location"]) for g in games]
 if len(set(dates))!=len(dates):raise RuntimeError("Duplicate games")
 return url, games
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--first",type=int,default=2016)
 parser.add_argument("--last",type=int,default=2026)
 args=parser.parse_args()
 s=requests.Session();s.headers["User-Agent"]="Mozilla/5.0"
 coverage={}; data={}
 for year in range(args.first,args.last+1):
  for slug in TEAMS:
   try:
    url,games=gather(s,slug,year)
    data.setdefault(slug,{})[str(year)]={"games":games,"source":url,"as_of":date_end(year),
      "scope":"TeamRankings historical dated snapshot; playoffs may be present"}
    coverage[f"{year}/{slug}"]={"games":len(games),"source":url}
    print(f"{year} {slug}: {len(games)}",flush=True)
   except Exception as exc:
    coverage[f"{year}/{slug}"]={"error":str(exc)}
    print(f"UNAVAILABLE {year} {slug}: {exc}",flush=True)
   time.sleep(1)
 OUT.mkdir(parents=True,exist_ok=True)
 for slug,seasons in data.items():
  path=OUT/f"{slug}-teamrankings-games.json"
  prior=json.loads(path.read_text()).get("seasons",{}) if path.exists() else {}
  prior.update(seasons)
  path.write_text(json.dumps({"team":slug,"seasons":prior},indent=2)+"\n")
 (OUT/"teamrankings-games-coverage.json").write_text(json.dumps(coverage,indent=2)+"\n")
 print(f"Validated team-seasons: {sum(len(x) for x in data.values())}/330",flush=True)
 if not data:raise RuntimeError("TeamRankings historical game logs inaccessible or changed layout")
if __name__=="__main__":main()
