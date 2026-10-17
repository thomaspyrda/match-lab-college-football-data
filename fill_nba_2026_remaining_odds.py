#!/usr/bin/env python3
"""Fill only missing 2025-26 NBA game odds after exact opponent, venue, date and score validation."""
import csv, io, json, math, urllib.request
from pathlib import Path
from collections import Counter
from audit_nba_2026_gap_source import DATA, URL, norm
ROOT=Path(__file__).resolve().parent

def main():
    req=urllib.request.Request(URL,headers={"User-Agent":"BetWise historical NBA audit"})
    with urllib.request.urlopen(req, timeout=75) as response:
        records=list(csv.DictReader(io.StringIO(response.read().decode("utf-8-sig"))))
    by_key={}
    for row in records:
        if str(row.get("season_type","")).lower() not in ("regular","regular season"):continue
        key=(row["date_et"][:10],norm(row["home_team"]),norm(row["away_team"]))
        by_key.setdefault(key,[]).append(row)
    totals=Counter(); teams={}
    for path in sorted(DATA.glob("*-season-details.json")):
        doc=json.loads(path.read_text()); team=path.name.removesuffix("-season-details.json")
        found=Counter()
        for g in doc.get("seasons",{}).get("2026",{}).get("games",[]):
            totals["games"]+=1
            if g.get("spread") is not None and g.get("total") is not None:
                totals["already_present"]+=1;continue
            candidates=[r for (date,home,away),rr in by_key.items()
              if date==g["date"] and (away if g["location"]=="Home" else home)==norm(g["opponent_name"]) for r in rr]
            matched=[]
            for r in candidates:
                try:
                    home_score=int(float(r["home_score"]));away_score=int(float(r["away_score"]))
                    h=g["score_for"] if g["location"]=="Home" else g["score_against"]
                    a=g["score_against"] if g["location"]=="Home" else g["score_for"]
                    if h==home_score and a==away_score:matched.append(r)
                except (KeyError,ValueError,TypeError):continue
            if len(matched)!=1:
                found["unmatched"]+=1;continue
            r=matched[0]
            try:
                home_line=float(r["close_spread_home"]);total=float(r["close_total"])
                if not math.isfinite(home_line) or not math.isfinite(total) or total<=0:raise ValueError("Invalid odds")
            except (ValueError,KeyError,TypeError):
                found["invalid_line"]+=1;continue
            team_line=home_line if g["location"]=="Home" else -home_line
            cover=g["score_for"]-g["score_against"]+team_line
            over=g["score_for"]+g["score_against"]-total
            g.update(spread=team_line,total=total,ats_result="W" if cover>0 else "L" if cover<0 else "P",
                ou_result="Over" if over>0 else "Under" if over<0 else "Push",
                odds_source="minmaxxxer NBA 2025-26 recorded lines",odds_source_url=URL,
                odds_line_type="source_labeled_closing_unverified")
            found["imported"]+=1
        teams[team]=dict(found);totals.update(found)
        if found["imported"]:
            path.write_text(json.dumps(doc,separators=(",",":"),ensure_ascii=False)+"\n")
    report={"totals":dict(totals),"teams":teams,"source":URL}
    (DATA/"2026-backfill-final-report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if totals["unmatched"] or totals["invalid_line"]:
        raise SystemExit("Some 2025-26 games still lack validated lines")
if __name__=="__main__":main()
