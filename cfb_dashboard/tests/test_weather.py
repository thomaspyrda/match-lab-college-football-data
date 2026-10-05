from datetime import datetime, timezone
from cfb_dashboard.pipeline.weather import weather_applicable, game_weather

def test_weather_only_applies_to_explicit_outdoor_home_venue():
    outdoor={"roof":"outdoors","latitude":33.7,"longitude":-84.4}
    assert weather_applicable(outdoor,False) is True
    assert weather_applicable(outdoor,True) is False
    assert weather_applicable({"roof":"indoor"},False) is False
    assert weather_applicable({},False) is False

def test_indoor_never_requests_forecast():
    text=game_weather({"roof":"dome"},datetime.now(timezone.utc),False)
    assert text=="Indoor/retractable roof · weather not applicable"

def test_unknown_venue_does_not_guess_weather():
    text=game_weather({},datetime.now(timezone.utc),False)
    assert text=="Venue weather unavailable"
