#!/usr/bin/env python3
"""Build CBB Match Lab archive only from independently verified pregame records.
Input: curated JSON {"games":[...]} with historical time-stamped snapshots.
This importer does NOT manufacture unavailable pregame metrics or results.
"""
import argparse,json,datetime
from pathlib import Path

def date(value):
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z","+00:00"))
    except (ValueError,TypeError):
        return None

def numeric(value):
    try:
        if value is None or value=="":return None
        return float(value)
    except (ValueError,TypeError):return None

def validated(g):
    r=g.get("result") or {}
    m=g.get("market") or {}
    tip=date(g.get("date") or g.get("kickoff"))
    snapshot=date(g.get("snapshot_as_of"))
    verified_time=date(g.get("result_verified_at"))
    away=numeric(r.get("away_points"));home=numeric(r.get("home_points"));total=numeric(m.get("total"))
    if not (tip and snapshot and verified_time and snapshot<tip<verified_time):return False
    if not g.get("pregame_verified") or r.get("verified") is not True:return False
    if not all([g.get("game_id"),g.get("away"),g.get("home"),g.get("pregame_source"),g.get("result_source"),g.get("market_source")]):return False
    if away is None or home is None or total is None:return False
    if away<0 or home<0 or total<=0:return False
    correct="over" if away+home>total else "under" if away+home<total else "push"
    return str(r.get("total","")).lower()==correct

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",default="cbb/match-lab/data/verified-historical.json")
    a=p.parse_args()
    games=json.loads(Path(a.input).read_text()).get("games",[])
    unique={}
    for g in games:
        if validated(g):unique[str(g["game_id"])]=g
    dst=Path(a.output);dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(json.dumps({"schema_version":1,"verified_only":True,"games":list(unique.values()),"source_file":a.input},separators=(",",":")))
    print(f"Verified {len(unique)} of {len(games)} supplied historical games")
if __name__=="__main__":main()
