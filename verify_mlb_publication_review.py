#!/usr/bin/env python3
"""Fail-closed verification of MLB review bundle; never deploy."""
import argparse,hashlib,json
from pathlib import Path

def verify(root,source_root):
    manifest=json.loads((root/"manifest.json").read_text())
    if manifest.get("status")!="REVIEW_ONLY_DO_NOT_DEPLOY" or manifest.get("requires_explicit_publication_authorization") is not True:
        raise ValueError("Unsafe review manifest")
    entries=manifest.get("files",[])
    if len(entries)!=30 or manifest.get("teams")!=30:
        raise ValueError("Expected 30 team entries")
    seen=set()
    for entry in entries:
        slug=entry["team"]
        if slug in seen or not slug or "/" in slug or ".." in slug:
            raise ValueError("Duplicate or unsafe team slug")
        seen.add(slug)
        source=source_root/"mlb"/"teams"/slug/"index.html"
        review=root/"mlb"/"teams"/slug/"index.html"
        if not source.is_file() or not review.is_file():
            raise ValueError("Missing source or review file: "+slug)
        if hashlib.sha256(source.read_bytes()).hexdigest()!=entry["source_sha256"]:
            raise ValueError("Source checksum changed: "+slug)
        if hashlib.sha256(review.read_bytes()).hexdigest()!=entry["review_sha256"]:
            raise ValueError("Review checksum mismatch: "+slug)
        if entry["path"]!=str(Path("mlb/teams")/slug/"index.html"):
            raise ValueError("Unexpected destination: "+slug)
    if sum(row["added_games"] for row in entries)!=manifest["games_added"]:
        raise ValueError("Incorrect game-entry total")
    return {"status":"REVIEW_PACKAGE_VERIFIED_NO_DEPLOYMENT","teams":30,"game_entries":manifest["games_added"],"published":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--review",default="mlb/data/publication-review")
    p.add_argument("--source",default=".")
    args=p.parse_args()
    print(json.dumps(verify(Path(args.review),Path(args.source))))
if __name__=="__main__":main()
