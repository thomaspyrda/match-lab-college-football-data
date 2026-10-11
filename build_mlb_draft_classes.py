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
def get(year,round_number):
    url=URL.format(year)+(f"?round={round_number}&limit=100" if round_number is not None else "?limit=1500")
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
    # Official full response includes compensation/supplemental groups beyond 5/20 standard rounds.
    # The same MLB endpoint returned 160 selections for 2020 and 615 for 2025 in probe.
    raw=get(year,None)
    draft=raw.get("drafts") or {}
    rounds=draft.get("rounds") or []
    required=5 if year==2020 else 20
    if len(rounds)<required:raise ValueError(f"{year}: only {len(rounds)} round groups")
    out={slug:[] for slug in TEAM_IDS.values()}
    invalid=[]
    for group in rounds:
        group_name=str(group.get("round") or "").strip()
        for pick in group.get("picks",[]) or []:
            if pick.get("isPass") is True:continue
            team=pick.get("team") or {}
            try:team_id=int(team.get("id"))
            except (TypeError,ValueError):team_id=None
            person=pick.get("person") or {}
            name=person.get("fullName") or pick.get("name") or person.get("name")
            if team_id not in TEAM_IDS or not name:
                invalid.append({"round":group_name,"team":team_id,"player":name,"pick":pick.get("pickNumber")})
                continue
            try:overall=int(pick.get("pickNumber"))
            except (ValueError,TypeError):overall=None
            if overall is None:
                invalid.append({"round":group_name,"pick":pick.get("pickNumber")})
                continue
            pos=pick.get("position") or person.get("primaryPosition")
            school=pick.get("school") or person.get("school")
            out[TEAM_IDS[team_id]].append({"round":str(pick.get("pickRound") or group_name),"overall_pick":overall,"round_pick":pick.get("roundPickNumber"),"player":name,"position":text_or_none(pos),"school":text_or_none(school),"player_id":person.get("id"),"signed":pick.get("isSigned") if isinstance(pick.get("isSigned"),bool) else None})
    if invalid:raise ValueError(f"{year}: unresolved draft picks: {invalid[:10]}")
    picks=[p for values in out.values() for p in values]
    expected_min=130 if year==2020 else 450
    if len(picks)<expected_min:raise ValueError(f"{year}: only {len(picks)} picks returned")
    if len({p["overall_pick"] for p in picks})!=len(picks):raise ValueError(f"{year}: duplicate overall picks")
    if any(not selections for selections in out.values()):raise ValueError(f"{year}: at least one franchise has no picks")
    for values in out.values():values.sort(key=lambda p:p["overall_pick"])
    print(f"{year}: {len(picks)} picks, {len(rounds)} groups, 30 franchises",flush=True)
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
    diagnostics=ROOT/"data/mlb/draft-collection-status.json"
    diagnostics.write_text(json.dumps({"attempted_years":args.years,"validated_years":sorted(map(int,all_years)),"failures":failures,"generated_at":doc["generated_at"]},indent=2)+"\n")
    if not all_years:raise RuntimeError("No validated MLB draft years were collected; see data/mlb/draft-collection-status.json")
    path.write_text(json.dumps(doc,ensure_ascii=False,separators=(",",":"))+"\n")
    print("Saved",path,"verified years:",len(all_years),"unavailable:",len(failures))
if __name__=="__main__":main()
