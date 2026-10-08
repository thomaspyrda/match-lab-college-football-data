#!/usr/bin/env python3
"""Collect NBA draft selections (2015–2026) from NBA.com Stats DraftHistory.
Output original drafting franchises, NOT post-draft trade destinations.
Missing values remain null; fail the build rather than publish partial coverage.
"""
import argparse,json,time,datetime
from pathlib import Path
from nba_api.stats.endpoints import drafthistory
from nba_api.stats.static import teams
ROOT=Path(__file__).resolve().parents[1]/"teams"/"data"
SLUGS={"ATL":"atlanta-hawks","BOS":"boston-celtics","BKN":"brooklyn-nets","CHA":"charlotte-hornets","CHI":"chicago-bulls","CLE":"cleveland-cavaliers","DAL":"dallas-mavericks","DEN":"denver-nuggets","DET":"detroit-pistons","GSW":"golden-state-warriors","HOU":"houston-rockets","IND":"indiana-pacers","LAC":"la-clippers","LAL":"los-angeles-lakers","MEM":"memphis-grizzlies","MIA":"miami-heat","MIL":"milwaukee-bucks","MIN":"minnesota-timberwolves","NOP":"new-orleans-pelicans","NYK":"new-york-knicks","OKC":"oklahoma-city-thunder","ORL":"orlando-magic","PHI":"philadelphia-76ers","PHX":"phoenix-suns","POR":"portland-trail-blazers","SAC":"sacramento-kings","SAS":"san-antonio-spurs","TOR":"toronto-raptors","UTA":"utah-jazz","WAS":"washington-wizards"}
ID_MAP={int(t["id"]):SLUGS[t["abbreviation"]] for t in teams.get_teams() if t["abbreviation"] in SLUGS}
def fetch(year):
    errors=[]
    for i in range(4):
        try:
            ep=drafthistory.DraftHistory(season_year_nullable=str(year),league_id_nullable="00",timeout=50)
            frames=ep.get_data_frames()
            if not frames or frames[0].empty:raise RuntimeError("empty NBA DraftHistory response")
            return frames[0].to_dict("records")
        except Exception as e:
            errors.append(str(e))
            time.sleep(3*(i+1))
    raise RuntimeError(f"{year}: NBA Stats request failed: {errors[-1]}")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,default=2015)
    p.add_argument("--end",type=int,default=2026)
    a=p.parse_args()
    result={slug:{str(year+1):[] for year in range(a.start,a.end+1)} for slug in SLUGS.values()}
    total=0; audit={}
    for year in range(a.start,a.end+1):
        rows=fetch(year)
        seen=set()
        for r in rows:
            if int(r.get("SEASON")) !=year:continue
            overall=int(r["OVERALL_PICK"]);rnd=int(r["ROUND_NUMBER"]);pick=int(r["ROUND_PICK"])
            if overall in seen:raise ValueError(f"{year}: duplicate overall pick {overall}")
            seen.add(overall)
            tid=int(r["TEAM_ID"])
            slug=ID_MAP.get(tid)
            if not slug:raise ValueError(f"{year}: team ID not recognized: {tid}")
            name=r.get("PLAYER_NAME")
            if not name:raise ValueError(f"{year} pick {overall}: missing player")
            result[slug][str(year+1)].append({
                "round":rnd,"pick":overall,"round_pick":pick,"player":str(name).strip(),
                "position":None,"college":r.get("ORGANIZATION") or None,
                "drafting_team_id":tid,"draft_year":year,
                "trade_note":None,
                "source":"https://www.nba.com/stats/draft/history?Season="+str(year)})
        # 2024+ NBA drafts have 58 or 59 picks due to forfeitures. Earlier ones
        # generally had 60. Reject truncated or duplicate result sets.
        expected_min=57 if year>=2024 else 59
        if len(seen)<expected_min or len(seen)>60:
            raise ValueError(f"{year}: unexpected pick count {len(seen)}; expected {expected_min}–60")
        if min(seen)!=1 or max(seen)<expected_min:
            raise ValueError(f"{year}: incomplete draft pick sequence")
        audit[year]=len(seen);total+=len(seen)
        print(year,len(seen),flush=True)
        time.sleep(.5)
    if len(result)!=30:raise ValueError("Missing NBA franchises")
    ROOT.mkdir(parents=True,exist_ok=True)
    for slug,seasons in result.items():
        for picks in seasons.values():picks.sort(key=lambda x:x["pick"])
        document={"team":slug,"draft_classes":seasons,"source":"NBA Stats Draft History",
          "draft_team_semantics":"original NBA selecting franchise; post-draft rights trades not reflected",
          "updated_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
        (ROOT/(slug+"-draft.json")).write_text(json.dumps(document,ensure_ascii=False,separators=(",",":"))+"\n")
    (ROOT/"draft-audit.json").write_text(json.dumps({"years":audit,"total":total,"teams":30},indent=2)+"\n")
    print(f"Validated {total} draft picks across {len(audit)} years for 30 NBA teams")
if __name__=="__main__":main()
