"""Read-only source audit of 2017-18 historical lines missing observed_at."""
import json
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parent
teams=json.loads((root/"data/sports/team-registry.json").read_text())["teams"]
counts=Counter();sample={}
for team in teams:
 if team.get("sport")!="cbb":continue
 path=root/f"data/cbb/markets/{team['slug']}.json"
 if not path.exists():continue
 for gid,row in json.loads(path.read_text()).get("games",{}).get("2018",{}).items():
  if not isinstance(row,dict):continue
  key=(row.get("line_type","UNSPECIFIED"),row.get("source","UNSPECIFIED"),"observed_at" in row)
  counts[key]+=1
  if key not in sample:sample[key]={"team":team["slug"],"game_id":gid,"market":row}
print("2017-18 historical market source and timestamp provenance:")
for key,n in counts.most_common():
 print(n,"line_type=",key[0],"source=",key[1],"has_observation_timestamp=",key[2])
 print(" Example:",json.dumps(sample[key],sort_keys=True)[:850])
print("No timestamp inferred; source-level evidence must be checked before changing verified eligibility.")
