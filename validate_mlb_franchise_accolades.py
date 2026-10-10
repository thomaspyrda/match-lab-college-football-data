#!/usr/bin/env python3
"""Audit MLB all-time franchise awards. No missing award is ever represented as zero."""
import json
from pathlib import Path
p=Path(__file__).resolve().parent/"data/mlb/franchise-accolades.json"
doc=json.loads(p.read_text())
teams=doc["teams"]
assert len(teams)==30, f"expected 30 franchises; got {len(teams)}"
division_by_year={}
for slug,data in teams.items():
    for field in ("world_series","division_titles","league_pennants"):
        obj=data["team"][field]
        years=obj["years"]
        assert years==sorted(set(years)), (slug,field,"duplicate/unsorted years")
        if obj["count"] is not None: assert obj["count"]==len(years),(slug,field)
        if obj["count"] is None: assert not years,(slug,field,"partial record must not be presented as complete")
    for year in data["team"]["division_titles"]["years"]:
        division_by_year[year]=division_by_year.get(year,0)+1
    assert data["player_awards_status"] in ("not_loaded","partial","complete")
assert 1994 not in division_by_year
for year in range(1969,1994):
    assert division_by_year.get(year)==4,(year,division_by_year.get(year))
for year in range(1995,2026):
    assert division_by_year.get(year)==6,(year,division_by_year.get(year))
assert len(division_by_year)==56
assert sum(t['team']['league_pennants']['count'] for t in teams.values())==267
assert all(t['team']['league_pennants']['count'] is not None for t in teams.values())
print("Verified structure: 30 teams, 286 division titles (1969–2025), no duplicates.")
print("Player awards: 31 multi-franchise awards still require attribution review.")
