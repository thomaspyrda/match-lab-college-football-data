#!/usr/bin/env python3
"""Build review-only MLB historical page publication bundle; never overwrite source pages."""
import argparse, hashlib, json
from pathlib import Path
from dry_run_mlb_page_updates import transform

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",default="mlb/data/historical-combined-preview.json")
    p.add_argument("--audit",default="mlb/data/historical-page-dry-run-report.json")
    p.add_argument("--out",default="mlb/data/publication-review")
    args=p.parse_args()
    archive=json.loads(Path(args.archive).read_text())
    audit=json.loads(Path(args.audit).read_text())
    if audit.get("publication_ready") is not True or audit.get("coverage_gate")!="PASS_STANDINGS_AND_STRUCTURE" or audit.get("teams")!=30:
        raise ValueError("Publication safety audit missing or failed")
    if archive.get("status")!="VERIFIED_STAGING_NO_PUBLICATION" or archive.get("years")!=list(range(2015,2026)):
        raise ValueError("Historical source archive not verified for all 11 seasons")
    pages=sorted(Path("mlb/teams").glob("*/index.html"))
    if len(pages)!=30:raise ValueError("Expected exactly 30 MLB team pages")
    out=Path(args.out)
    entries=[]
    for source in pages:
        before=source.read_bytes()
        modified,report=transform(before.decode("utf-8"),archive,source.parent.name)
        after=modified.encode("utf-8")
        target=out/"mlb"/"teams"/source.parent.name/"index.html"
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(after)
        entries.append({"team":source.parent.name,"path":str(source),
            "source_sha256":hashlib.sha256(before).hexdigest(),
            "review_sha256":hashlib.sha256(after).hexdigest(),
            "added_games":report["added_regular_games"]})
    manifest={"status":"REVIEW_ONLY_DO_NOT_DEPLOY","source":"2015-2025 verified historical archive",
        "teams":30,"games_added":sum(x["added_games"] for x in entries),
        "requires_explicit_publication_authorization":True,"files":entries}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"status":manifest["status"],"teams":30,"games_added":manifest["games_added"],"published":False}))
if __name__=="__main__":main()
