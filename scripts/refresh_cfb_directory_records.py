#!/usr/bin/env python3
"""Refresh CFB directory W-L badges from completed season results, preserving strength ranks."""
import json,re,datetime,pathlib,collections
root=pathlib.Path(__file__).resolve().parents[1]
source=json.loads((root/"data/historical/2026.json").read_text())
registry=json.loads((root/"data/cfb/team-registry.json").read_text())["teams"]
byid={str(t["id"]):t["name"] for t in registry}
records=collections.defaultdict(lambda:[0,0,0])
latest=None
seen=set()
for g in source["games"]:
    result=g.get("result") or {}
    if not result:continue
    hp=result.get("home_points")
    ap=result.get("away_points")
    if hp is None or ap is None:continue
    gid=str(g.get("game_id"))
    if gid in seen:continue
    seen.add(gid)
    start=str(g.get("start_date") or "")
    if start:
        dt=datetime.datetime.fromisoformat(start.replace("Z","+00:00")).date()
        latest=max(dt,latest) if latest else dt
    for side,for_score,against in (("home",hp,ap),("away",ap,hp)):
        tid=str(g.get(side+"_id"))
        if tid not in byid:continue
        rec=records[byid[tid]]
        rec[0 if for_score>against else 1 if for_score<against else 2]+=1
if not latest or latest<datetime.date(2026,10,17):
    raise SystemExit(f"Historical 2026 dataset stale; latest completed date is {latest}; refusing to publish outdated records")
page=root/"teams.html"
html=page.read_text()
changes=[]
def patch(m):
    name=m.group(2).strip()
    values=records.get(name)
    if not values:return m.group(0)
    w,l,t=values
    new=f"{w}-{l}"+(f"-{t}" if t else "")
    if m.group(3)!=new:changes.append((name,m.group(3),new))
    return m.group(1)+new+m.group(4)
pattern=r'(<strong>([^<]+)</strong><small>)(\d+-\d+(?:-\d+)?)(\s*·\s*Team Strength #\d+</small>)'
html,count=re.subn(pattern,patch,html)
assert count>=125,(count,changes)
assert len(records)>=125,len(records)
print("Records already current" if not changes else "Applying directory record updates")
page.write_text(html)
print(json.dumps({"latest_completed_date":str(latest),"teams_with_records":len(records),"tiles_found":count,"records_updated":len(changes),"changes":changes[:40]},indent=2))
