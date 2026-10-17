#!/usr/bin/env python3
"""Read-only predeployment source drift check; never applies or deploys reviewed files."""
import argparse,hashlib,json
from pathlib import Path

def check(review_root,source_root):
    manifest=json.loads((review_root/"manifest.json").read_text())
    if manifest.get("status")!="REVIEW_ONLY_DO_NOT_DEPLOY" or manifest.get("requires_explicit_publication_authorization") is not True:
        raise ValueError("Review-only manifest required")
    entries=manifest.get("files",[])
    if len(entries)!=30 or len({entry["team"] for entry in entries})!=30:
        raise ValueError("Expected thirty unique teams")
    changes=[]
    for entry in entries:
        slug=entry["team"]
        if not slug or "/" in slug or ".." in slug: raise ValueError("Unsafe team slug")
        expected=Path("mlb")/"teams"/slug/"index.html"
        if entry["path"]!=str(expected): raise ValueError("Unexpected source path")
        path=source_root/expected
        if not path.is_file(): raise ValueError("Original page missing: "+slug)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=entry["source_sha256"]:
            changes.append({"team":slug,"reason":"SOURCE_CHANGED_SINCE_REVIEW"})
    return {"status":"BLOCKED_SOURCE_DRIFT" if changes else "SOURCE_UNCHANGED_NO_DEPLOYMENT",
            "teams_checked":30,"changed":changes,"published":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--review",default="mlb/data/publication-review")
    p.add_argument("--source",default=".")
    args=p.parse_args()
    result=check(Path(args.review),Path(args.source))
    print(json.dumps(result))
    if result["changed"]:raise SystemExit("Source drift: rebuild and review before any deployment")
if __name__=="__main__":main()
