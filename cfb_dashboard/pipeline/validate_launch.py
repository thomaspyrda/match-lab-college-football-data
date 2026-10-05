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
    assert len(g["matchup_metrics"]) == 11
    for metric in g["matchup_metrics"][:3]:
        for side in ("away_offense", "home_defense", "home_offense", "away_defense"):
            assert isinstance(metric.get(side), (int, float)), (g["game_id"], metric["label"], side)
    assert isinstance(g.get("market"),dict)
    assert isinstance(g.get("context"),dict)
    assert isinstance(g.get("weather"),dict)
    assert isinstance(g.get("trends"),list)
    assert len(g.get("players", [])) == 10, g["game_id"]
    for group in (g["players"][:5],g["players"][5:]):
        assert [p["position"] for p in group[:4]] == ["QB","RB","WR","TE"]
        ids=[str(p.get("player_id") or p.get("name")) for p in group if not p.get("placeholder")]
        assert len(ids)==len(set(ids)), (g["game_id"],ids)
        metric=group[0].get("efficiency")
        if metric and metric.get("rank"):
            assert metric["qualified"] and metric["sample_size"] >= metric["minimum"]
missing=sum(1 for g in d["games"] if not any(
    isinstance(v,(int,float))
    for m in g["matchup_metrics"]
    for v in (m.get("away_offense"),m.get("home_defense"),m.get("home_offense"),m.get("away_defense"))
))
assert missing==0, f"{missing} games have no usable matchup metrics"
print(f'Validated {len(d["games"])} CFB Dashboard matchups')
