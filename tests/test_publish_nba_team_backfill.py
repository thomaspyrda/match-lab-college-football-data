import json, tempfile, unittest
from pathlib import Path
from publish_nba_team_backfill import apply_manifest

class PublishNBAUnitTests(unittest.TestCase):
    def test_add_and_reapply(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            teams={}
            for i in range(30):
                slug=f"team-{i}"
                (p/(slug+"-season-details.json")).write_text(json.dumps({"seasons":{"2026":{"games":[]}}}))
                teams[slug]=[{"game_id":str(i),"date":"2026-10-20","location":"Home","opponent_slug":"team-1","result":"W","score_for":110,"score_against":100,"spread":None,"total":None,"ats_result":None,"ou_result":None}] if i==0 else []
            m={"season":2027,"status":"STAGING_NOT_PUBLISHED","teams":teams}
            result=apply_manifest(m,p,write=True)
            self.assertEqual(result["added"],1)
            self.assertEqual(apply_manifest(m,p,write=True)["existing"],1)
            obj=json.loads((p/"team-0-season-details.json").read_text())
            self.assertEqual(obj["seasons"]["2027"]["record"],"1–0")
            self.assertIn("2026",obj["seasons"])
    def test_reject_wrong_year(self):
        with self.assertRaises(ValueError):
            apply_manifest({"season":2026,"status":"STAGING_NOT_PUBLISHED","teams":{}})

if __name__=="__main__":unittest.main()
