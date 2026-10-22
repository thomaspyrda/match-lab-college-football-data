"""Read only explicit archived closing lines from ESPN game summaries."""
import math

def number(value, prefix=''):
    if value is None or isinstance(value,bool): return None
    text=str(value).strip()
    if prefix and text.lower().startswith(prefix):text=text[1:]
    if text.upper() in ('PK','PICK','PICK\'EM'):return 0.0
    try: value=float(text)
    except (ValueError,TypeError):return None
    return value if math.isfinite(value) else None

def closing_market(summary, event_id, observed_at):
    for quote in summary.get('pickcenter') or []:
        spread=quote.get('pointSpread') or {};total=quote.get('total') or {}
        home=number(spread.get('home',{}).get('close',{}).get('line'))
        away=number(spread.get('away',{}).get('close',{}).get('line'))
        over=number(total.get('over',{}).get('close',{}).get('line'),'o')
        under=number(total.get('under',{}).get('close',{}).get('line'),'u')
        # Contradictory sides are not a trustworthy archived market.
        if home is not None and away is not None and abs(home+away)>.001:home=None;away=None
        if home is None and away is not None:home=-away
        if over is not None and under is not None and abs(over-under)>.001:over=None;under=None
        line=over if over is not None else under
        if line is not None and line<=0:line=None
        if home is None and line is None:continue
        return {'home_spread':home,'total':line,'provider':quote.get('provider',{}).get('name'),
                'line_type':'closing','source':'https://www.espn.com/nba/game/_/gameId/'+str(event_id),
                'observed_at':observed_at,'evidence':'ESPN pickcenter pointSpread/total close.line'}
    return None

def verified_closing_market(game):
    market=game.get('closing_market') or {}
    if (market.get('line_type')!='closing' or market.get('source')!='https://www.espn.com/nba/game/_/gameId/'+str(game['id'])
        or market.get('evidence')!='ESPN pickcenter pointSpread/total close.line' or not market.get('observed_at')):return None
    for key in ('home_spread','total'):
        if market.get(key) is not None and number(market[key]) is None:return None
    return market if market.get('home_spread') is not None or market.get('total') is not None else None
