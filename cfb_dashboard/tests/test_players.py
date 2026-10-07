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


def test_ten_attempt_qualification_boundary():
    teams={'A':[{'id':'a','position':'QB'},{'id':'b','position':'QB'}]}
    ppa=[{'team':'A','id':pid,'averagePPA':{'pass':value}} for pid,value in [('a',.4),('b',.9)]]
    enrich_players(teams,ppa,{('A','a'):10,('A','b'):9},{'A':{1,2,3,4,5,6}}, {}, {}, {}, {'A'})
    assert teams['A'][0]['efficiency']['rank']==1
    assert teams['A'][1]['efficiency']['rank'] is None
    assert teams['A'][0]['efficiency']['qualifying_count']==1

def test_season_production_join_and_team_game_averages():
    from cfb_dashboard.pipeline.players import enrich_production
    teams={'A':[{'id':'1','name':'Same Name'},{'id':'2','name':'Missing Player'}],
           'B':[{'id':'1','name':'Same Name'}]}
    stats=[{'team':'A','playerId':'1','player':'Same Name','category':'passing','statType':'C/ATT','stat':'18/25'},
           {'team':'A','playerId':'1','category':'passing','statType':'YDS','stat':'1,200'},
           {'team':'A','playerId':'1','category':'passing','statType':'INT','stat':'0'},
           {'team':'B','playerId':'1','category':'receiving','statType':'YDS','stat':'300'}]
    games=[{'game_id':1,'home':'A','away':'B','result':{'home_points':10}},
           {'game_id':2,'home':'A','away':'C','result':{'home_points':20}},
           {'game_id':3,'home':'A','away':'B','result':None}]
    enrich_production(teams,stats,games)
    a=teams['A'][0]['production']
    assert a['totals']['completions']==18 and a['totals']['attempts']==25
    assert a['totals']['interceptions']==0
    assert a['per_game']['passing_yards']==600 and a['team_games']==2
    assert teams['B'][0]['production']['per_game']['receiving_yards']==300
    assert teams['A'][1]['production']['totals']['passing_yards'] is None
    assert a['totals']['rushing_yards'] is None


def test_conflicting_player_stat_is_rejected():
    import pytest
    from cfb_dashboard.pipeline.players import enrich_production
    stats=[{'team':'A','playerId':'1','category':'rushing','statType':'YDS','stat':n} for n in (100,200)]
    with pytest.raises(ValueError,match='Conflicting season player stat'):
        enrich_production({},stats,[])
