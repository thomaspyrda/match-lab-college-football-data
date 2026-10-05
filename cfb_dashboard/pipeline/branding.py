"""Current team branding for the CFB Dashboard.

Logos are resolved from ESPN's current college-football team IDs rather than
hard-coded image filenames. Cache the resulting mapping in generated dashboard
data so the browser does not need to discover IDs itself.
"""
from __future__ import annotations
import json, urllib.request
from pathlib import Path

ESPN_TEAMS="https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/teams?limit=500"
ALIASES={
    "UConn":"Connecticut","Ole Miss":"Mississippi","UTSA":"Texas-San Antonio",
    "Appalachian State":"App State","FIU":"Florida International",
    "San Jose State":"San José State",
}

def norm(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())

def fetch_current_branding() -> dict[str, dict]:
    req=urllib.request.Request(ESPN_TEAMS,headers={"User-Agent":"BetWise-CFB-Dashboard/1.0"})
    with urllib.request.urlopen(req,timeout=60) as response:
        payload=json.load(response)
    out={}
    for item in payload.get("sports",[{}])[0].get("leagues",[{}])[0].get("teams",[]):
        team=item.get("team") or {}
        names={team.get("displayName"),team.get("shortDisplayName"),team.get("location"),team.get("name"),team.get("abbreviation")}
        logo=next((x.get("href") for x in team.get("logos",[]) if x.get("href")),None)
        row={"espn_id":team.get("id"),"display_name":team.get("displayName"),"abbreviation":team.get("abbreviation"),
             "logo":logo,"color":team.get("color"),"alternate_color":team.get("alternateColor"),"source":"ESPN current team feed"}
        for name in filter(None,names):
            out[norm(name)]=row
    return out

def resolve(team: str, branding: dict[str,dict]) -> dict:
    candidates=[team,ALIASES.get(team,team)]
    for candidate in candidates:
        row=branding.get(norm(candidate))
        if row:return row
    return {"espn_id":None,"display_name":team,"abbreviation":None,"logo":None,"color":None,"alternate_color":None,"source":None}

def write_cache(path: Path) -> None:
    data=fetch_current_branding()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({"source":ESPN_TEAMS,"teams":data},indent=2),encoding="utf-8")
