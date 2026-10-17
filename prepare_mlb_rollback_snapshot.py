#!/usr/bin/env python3
"""Prepare a local, nondeploying rollback manifest for MLB historical review pages.

Approval and deployment are intentionally NOT implemented here.
"""
import argparse,hashlib,json
from pathlib import Path
from verify_mlb_publication_review import verify

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--review",default="mlb/data/publication-review")
    p.add_argument("--source",default=".")
    a=p.parse_args()
    root=Path(a.review);source=Path(a.source)
    verify(root,source)
    manifest=json.loads((root/"manifest.json").read_text())
    rollback=root/"rollback-originals"
    records=[]
    for entry in manifest["files"]:
        slug=entry["team"]
        original=source/"mlb"/"teams"/slug/"index.html"
        destination=rollback/"mlb"/"teams"/slug/"index.html"
        destination.parent.mkdir(parents=True,exist_ok=True)
        data=original.read_bytes()
        if hashlib.sha256(data).hexdigest()!=entry["source_sha256"]:
            raise ValueError("Source drift before rollback snapshot: "+slug)
        destination.write_bytes(data)
        records.append({"team":slug,"original_sha256":entry["source_sha256"],
                        "review_sha256":entry["review_sha256"],"rollback_path":str(destination.relative_to(root))})
    (root/"rollback-manifest.json").write_text(json.dumps({
        "status":"ROLLBACK_SNAPSHOT_ONLY_NO_DEPLOYMENT",
        "approval_required":True,"files":records},indent=2)+"\n")
    print(json.dumps({"status":"ROLLBACK_SNAPSHOT_ONLY_NO_DEPLOYMENT","teams":len(records),"published":False}))
if __name__=="__main__":main()
