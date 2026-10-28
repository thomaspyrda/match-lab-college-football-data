"""Box-score-derived basketball metrics with complete-sample coverage checks."""
import math

# Rows remain offensive/defensive pairs; neutral team context follows the pairs.
ADDITIONAL_METRICS = [
 ('points_in_paint','Points in the Paint','OFFENSE',True,''),
 ('opp_points_in_paint','Points in the Paint Allowed','DEFENSE',False,''),
 ('three_attempt_rate','3P Rate','OFFENSE',True,'%'),
 ('opp_three_attempt_rate','3P Rate Allowed','DEFENSE',False,'%'),
 ('rebounds_per_game','Rebounds/Game','OFFENSE',True,''),
 ('opp_rebounds_per_game','Rebounds Allowed/Game','DEFENSE',False,''),
 ('total_rebound_rate','Total Rebound Rate','OFFENSE',True,'%'),
 ('opp_total_rebound_rate','Rebound Share Allowed','DEFENSE',False,'%'),
 ('turnovers_per_game','Turnovers/Game','OFFENSE',False,''),
 ('opp_turnovers_per_game','Turnovers Forced/Game','DEFENSE',True,''),
 ('turnover_margin','Turnover Margin','TEAM',True,''),
]


def derived_metrics(games, team_id):
    """Use only the caller's season/phase/cutoff-filtered completed sample.

    A missing box-score field makes its season metric unavailable rather than
    silently dividing a partial total by the complete game count.
    """
    own = [g['teams'][team_id] for g in games]
    opponents = [g['teams'][next(t for t in g['teams'] if t != team_id)] for g in games]

    def total(rows, field):
        values = [r.get(field) for r in rows]
        return sum(values) if values and all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in values) else None

    def ratio(a, b, scale=1):
        return a / b * scale if a is not None and b else None

    n = len(games)
    rebounds, opp_rebounds = total(own, 'reb'), total(opponents, 'reb')
    turnovers, forced = total(own, 'tov'), total(opponents, 'tov')
    rebound_sum = rebounds + opp_rebounds if rebounds is not None and opp_rebounds is not None else None
    return {
      'points_in_paint': ratio(total(own, 'paint_points'), n),
      'opp_points_in_paint': ratio(total(opponents, 'paint_points'), n),
      'three_attempt_rate': ratio(total(own, 'tpa'), total(own, 'fga'), 100),
      'opp_three_attempt_rate': ratio(total(opponents, 'tpa'), total(opponents, 'fga'), 100),
      'rebounds_per_game': ratio(rebounds, n),
      'opp_rebounds_per_game': ratio(opp_rebounds, n),
      'total_rebound_rate': ratio(rebounds, rebound_sum, 100),
      'opp_total_rebound_rate': ratio(opp_rebounds, rebound_sum, 100),
      'turnovers_per_game': ratio(turnovers, n),
      'opp_turnovers_per_game': ratio(forced, n),
      'turnover_margin': (forced - turnovers) / n if n and forced is not None and turnovers is not None else None,
    }
