import json
from pathlib import Path

p=Path("cfb_dashboard/data/dashboard.json")
d=json.loads(p.read_text(encoding="utf-8"))
assert isinstance(d.get("games"),list)
assert d.get("slate",{}).get("model_version")=="v15", d.get("slate")
for g in d["games"]:
    assert g.get("away",{}).get("name")
    assert g.get("home",{}).get("name")
    assert g.get("away",{}).get("espn_id"), g["away"]["name"]
    assert g.get("home",{}).get("espn_id"), g["home"]["name"]
    assert isinstance(g.get("matchup_metrics"),list)
    assert isinstance(g.get("market"),dict)
    assert isinstance(g.get("context"),dict)
    assert isinstance(g.get("weather"),dict)
    assert isinstance(g.get("trends"),list)
missing=sum(1 for g in d["games"] if not any(
    isinstance(v,(int,float))
    for m in g["matchup_metrics"]
    for v in (m.get("away_offense"),m.get("home_defense"),m.get("home_offense"),m.get("away_defense"))
))
assert missing==0, f"{missing} games have no usable matchup metrics"
print(f'Validated {len(d["games"])} CFB Dashboard matchups')
