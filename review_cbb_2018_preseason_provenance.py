"""Nonpublishing provenance review for historical preseason candidate captures.
Does not infer original publication date from the Wayback capture date.
"""
import argparse,json,re
from pathlib import Path

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--staged",type=Path,required=True)
 p.add_argument("--output",type=Path,default=Path("cbb/match-lab/imports/preseason-review/2018-provenance-review.json"))
 a=p.parse_args();d=json.loads(a.staged.read_text())
 if len(d["rankings"])!=351 or d.get("publication_allowed") is not False:raise ValueError("Staging safeguards missing")
 url=d.get("source_url","")
 expected="trankpure18.php"
 if expected not in url:raise ValueError("Unexpected Torvik archived source URL")
 capture=re.search(r"/web/(\d{14})",url)
 if not capture:raise ValueError("Capture timestamp missing")
 archive_year=int(capture.group(1)[:4])
 report={"season":2018,"rankings_checked":351,"source_path_verified":True,
  "archive_capture_year":archive_year,
  "archive_capture_is_after_2017_preseason":archive_year>2017,
  "original_preseason_provenance_verified":False,
  "reuse_permission_verified":False,
  "ready_for_publication":False,
  "notes":"Original Torvik preseason page URL is verified, but a 2020 archive capture alone cannot prove unchanged 2017 preseason values. Manual source confirmation and redistribution approval required."}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(report,indent=2)+"\n")
 print("PROVENANCE REVIEW:",json.dumps(report))
if __name__=="__main__":main()
