#!/usr/bin/env python3
"""Create local-only representative MLB team HTML previews from audited archive."""
import argparse,json
from pathlib import Path
from dry_run_mlb_page_updates import transform

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",default="mlb/data/historical-combined-preview.json")
    p.add_argument("--out",default="mlb/data/html-preview")
    args=p.parse_args()
    archive=json.loads(Path(args.archive).read_text())
    out=Path(args.out)
    slugs=("atlanta-braves","chicago-cubs","detroit-tigers")
    manifest={}
    for slug in slugs:
        original=Path("mlb/teams")/slug/"index.html"
        html,report=transform(original.read_text(),archive,slug)
        target=out/"mlb"/"teams"/slug/"index.html"
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(html)
        manifest[slug]=report
    (out/"preview-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"status":"LOCAL_PREVIEW_ONLY","teams":list(manifest),"published":False}))
if __name__=="__main__":main()
