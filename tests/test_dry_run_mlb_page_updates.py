import json,re,unittest
from dry_run_mlb_page_updates import transform,PATTERN

def html():
    d={"team_id":"mlb:espn:1","seasons":[{"key":"2026","games":[],"coverage":"not_loaded"}]}
    return '<html><script type="application/json" id="team-season-data">'+json.dumps(d)+'</script><p>unchanged</p></html>'
def archive(phase="regular",runs=5):
    return {"games":{"9":{"game_id":"9","date":"2026-10-01","season":2026,"phase":phase,
      "home":{"slug":"baltimore-orioles","runs":runs},"away":{"slug":"boston-red-sox","runs":2},"source":"test"}}}
def parsed(s):return json.loads(PATTERN.search(s).group(2))

class MLBPageSafety(unittest.TestCase):
    def test_regular_idempotent(self):
        h=html();a=archive()
        once,report=transform(h,a,"baltimore-orioles")
        self.assertEqual(report["added_regular_games"],1)
        twice,report=transform(once,a,"baltimore-orioles")
        self.assertEqual(report["added_regular_games"],0)
        self.assertEqual(parsed(twice)["seasons"][0]["games"][0]["score"],"5–2")
        self.assertIn("<p>unchanged</p>",twice)
    def test_postseason_not_in_regular_season(self):
        output,report=transform(html(),archive("world_series"),"baltimore-orioles")
        self.assertEqual(parsed(output)["seasons"][0]["games"],[])
        self.assertEqual(report["postseason_games_not_merged"],1)
    def test_conflicting_existing_score_rejected(self):
        once,_=transform(html(),archive(),"baltimore-orioles")
        with self.assertRaisesRegex(ValueError,"score"):
            transform(once,archive(runs=6),"baltimore-orioles")
    def test_conflicting_existing_location_rejected(self):
        once,_=transform(html(),archive(),"baltimore-orioles")
        data=json.loads(PATTERN.search(once).group(2))
        data["seasons"][0]["games"][0]["location"]="Away"
        changed=PATTERN.sub(lambda m:m.group(1)+json.dumps(data)+m.group(3),once)
        with self.assertRaisesRegex(ValueError,"location"):
            transform(changed,archive(),"baltimore-orioles")
    def test_conflicting_existing_result_rejected(self):
        once,_=transform(html(),archive(),"baltimore-orioles")
        with self.assertRaises(ValueError):
            transform(once,archive(runs=1),"baltimore-orioles")

if __name__=="__main__":unittest.main()
