from cfb_dashboard.pipeline.players import select_players, enrich_players
from cfb_dashboard.pipeline.availability import current_reports
from datetime import datetime, timezone

def test_role_slots_injury_replacements_and_no_duplicates():
    rows=[{'id':'out','position':'WR','overall':.99,'unavailable':True},
          {'id':'q1','position':'QB','pass':.9,'recent_passing_role':(3,30)},
          {'id':'q2','position':'QB','pass':.2,'recent_passing_role':(4,20)},
          {'id':'r','position':'RB','overall':.5},{'id':'w','position':'WR','overall':.4},
          {'id':'t','position':'TE','overall':.1},{'id':'w2','position':'WR','overall':.3}]
    selected=select_players(rows)
    assert [row['id'] for row in selected]==['q2','r','w','t','w2']

def test_qualified_rank_ties_and_small_sample():
    teams={'A':[{'id':'a','position':'QB'},{'id':'b','position':'QB'},{'id':'c','position':'QB'},{'id':'d','position':'QB'}]}
    ppa=[{'team':'A','id':pid,'averagePPA':{'pass':value}} for pid,value in [('a',.4),('b',.4),('c',.2),('d',.9)]]
    enrich_players(teams,ppa,{('A','a'):60,('A','b'):60,('A','c'):60,('A','d'):2},{'A':{1,2,3}}, {}, {}, {}, {'A'})
    assert [row['efficiency']['rank'] for row in teams['A']]==[1,1,3,None]
    assert teams['A'][3]['efficiency']['qualified'] is False

def test_stale_out_report_is_ignored():
    payload={'injuries':[{'id':'1','injuries':[{'date':'2020-10-01T00:00:00Z','status':'Out','athlete':{'id':'a'}}]}]}
    assert current_reports(payload,datetime(2026,10,5,tzinfo=timezone.utc),'college-football')=={}
