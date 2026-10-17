#!/usr/bin/env python3
"""Independent audit of offline MLB rollback snapshot; never publishes files."""
import argparse,hashlib,json
from pathlib import Path

def verify(root):
    review=json.loads((root/"manifest.json").read_text())
    rollback=json.loads((root/"rollback-manifest.json").read_text())
    if rollback.get("status")!="ROLLBACK_SNAPSHOT_ONLY_NO_DEPLOYMENT" or rollback.get("approval_required") is not True:
        raise ValueError("Unsafe rollback manifest")
    original={x["team"]:x for x in review["files"]}
    entries=rollback.get("files",[])
    if len(entries)!=30 or len(original)!=30 or len({x["team"] for x in entries})!=30:
        raise ValueError("Expected thirty distinct rollback files")
    for entry in entries:
        team=entry["team"]
        if team not in original:raise ValueError("Unexpected team in rollback")
        expected=original[team]
        if entry["original_sha256"]!=expected["source_sha256"] or entry["review_sha256"]!=expected["review_sha256"]:
            raise ValueError("Rollback source-to-review checksum mismatch: "+team)
        expected_path=Path("rollback-originals/mlb/teams")/team/"index.html"
        if entry["rollback_path"]!=str(expected_path):
            raise ValueError("Unsafe rollback path: "+team)
        file=root/expected_path
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=entry["original_sha256"]:
            raise ValueError("Rollback file missing or corrupted: "+team)
    return {"status":"ROLLBACK_VERIFIED_NO_DEPLOYMENT","teams":30,"published":False}

def main():
    p=argparse.ArgumentParser();p.add_argument("--review",default="mlb/data/publication-review")
    print(json.dumps(verify(Path(p.parse_args().review))))
if __name__=="__main__":main()
