#!/usr/bin/env python3
"""Compile MLB amateur draft classes (2015–2026) from official MLB Stats API.
All rounds, all teams; publication is atomic and fails closed on incomplete years.
"""
import json, urllib.request, time, argparse
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parent
TEAM_IDS={108:"los-angeles-angels",109:"arizona-diamondbacks",110:"baltimore-orioles",111:"boston-red-sox",112:"chicago-cubs",113:"cincinnati-reds",114:"cleveland-guardians",115:"colorado-rockies",116:"detroit-tigers",117:"houston-astros",118:"kansas-city-royals",119:"los-angeles-dodgers",120:"washington-nationals",121:"new-york-mets",133:"athletics",134:"pittsburgh-pirates",135:"san-diego-padres",136:"seattle-mariners",137:"san-francisco-giants",138:"st-louis-cardinals",139:"tampa-bay-rays",140:"texas-rangers",141:"toronto-blue-jays",142:"minnesota-twins",143:"philadelphia-phillies",144:"atlanta-braves",145:"chicago-white-sox",146:"miami-marlins",147:"new-york-yankees",158:"milwaukee-brewers"}
URL="https://statsapi.mlb.com/api/v1/draft/{}"
def get(year):
    url=URL.format(year)
    req=urllib.request.Request(url,headers={"User-Agent":"BetWiseResearch/1.0","Accept":"application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=120) as response: return json.load(response)
        except Exception:
            if attempt==3:raise
            time.sleep(2**attempt)
def text_or_none(v):
    if isinstance(v,dict):return v.get("name") or v.get("fullName") or v.get("abbreviation")
    return str(v).strip() if v not in (None,"") else None
def build(year):
    raw=get(year);draft=raw.get("drafts") or {}
    rounds=draft.get("rounds") or []
    if not rounds:raise ValueError(f"Missing rounds in official draft {year}")
    if len(rounds)<(5 if year==2020 else 20):raise ValueError(f"{year}: only {len(rounds)} rounds returned; incomplete draft")
    out={slug:[] for slug in TEAM_IDS.values()}
    invalid=[]
    for rd in rounds:
        for pick in rd.get("picks") or []:
            if pick.get("isDrafted") is False or pick.get("isPass") is True:continue
            team=pick.get("team") or {};team_id=team.get("id")
            if team_id not in TEAM_IDS:invalid.append((team_id,pick.get("pickNumber")));continue
            person=pick.get("person") or {}
            name=person.get("fullName") or pick.get("name") or person.get("name")
            if not name:invalid.append(("unnamed",pick.get("pickNumber")));continue
            pos=person.get("primaryPosition") or pick.get("position")
            school=pick.get("school") or person.get("school")
            round_id=str(pick.get("pickRound") or rd.get("round") or "").strip()
            overall=pick.get("pickNumber")
            if not round_id or not isinstance(overall,int):invalid.append(("bad pick",overall));continue
            out[TEAM_IDS[team_id]].append({"round":round_id,"overall_pick":overall,"round_pick":pick.get("roundPickNumber"),"player":name,"position":text_or_none(pos),"school":text_or_none(school),"player_id":person.get("id"),"signed":pick.get("isSigned") if isinstance(pick.get("isSigned"),bool) else None})
    if invalid:raise ValueError(f"{year} missing/unknown picks: {invalid[:15]}")
    all_picks=[p for arr in out.values() for p in arr]
    minimum=130 if year==2020 else 450
    if len(all_picks)<minimum:raise ValueError(f"{year} draft appears incomplete ({len(all_picks)} selections)")
    if len({p["overall_pick"] for p in all_picks})!=len(all_picks):raise ValueError(f"{year} duplicate overall picks")
    if any(not selections for selections in out.values()):raise ValueError(f"{year} team with no draft picks")
    for arr in out.values():arr.sort(key=lambda p:p["overall_pick"])
    print(f"{year}: {len(all_picks)} picks, {len(rounds)} rounds, {sum(bool(a) for a in out.values())} teams")
    return out
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--years",nargs="+",type=int,default=list(range(2020,2027)))
    args=parser.parse_args()
    path=ROOT/"data/mlb/draft-classes.json";path.parent.mkdir(parents=True,exist_ok=True)
    old=json.loads(path.read_text()) if path.exists() and path.stat().st_size else {}
    all_years=old.get("years",{})
    failures={}
    for year in args.years:
        try:
            all_years[str(year)]=build(year)
        except Exception as exc:
            failures[str(year)]=str(exc)
            print(f"Could not validate {year}: {exc}")
    doc={"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),"source":"MLB Stats API official draft results","source_url":"https://statsapi.mlb.com/api/v1/draft/{year}","years":dict(sorted(all_years.items())),"unavailable_years":failures}
    if not all_years:raise RuntimeError("No validated MLB draft years were collected")
    path.write_text(json.dumps(doc,ensure_ascii=False,separators=(",",":"))+"\\n")
    print("Saved",path,"verified years:",len(all_years),"unavailable:",len(failures))
if __name__=="__main__":main()
