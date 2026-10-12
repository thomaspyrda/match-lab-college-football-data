import json,pathlib
r=pathlib.Path(__file__).resolve().parent
src=r/'data/experiments/recursive_unit_strength_v15_2026_week_7.json'
j=json.loads(src.read_text())
out={'model':'Original v15 41-metric week-7 pregame snapshot','pregame_week':j['pregame_week'],'through_week':j['through_week'],'top50':[{'rank':i+1,'team':x['team'],'strength_sd':x['overall_team_strength_sd'],'offense_rank':x['offense_rank'],'defense_rank':x['defense_rank']} for i,x in enumerate(j['rankings'][:50])]}
p=r/'data/experiments/fullmetric_week7_top50_2026.json'
p.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))

# Trigger export.
