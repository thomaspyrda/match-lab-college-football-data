#!/usr/bin/env python3
"""Fail unless completed MLB season files match the approved SHA-256 manifest.
A correction requires an explicit manifest refresh in a reviewed commit.
"""
import hashlib,json,pathlib,sys
root=pathlib.Path(__file__).resolve().parents[1]
manifest=root/"data/mlb/frozen-season-sha256.json"
expected=json.loads(manifest.read_text())["seasons"]
bad=[]
for year,digest in expected.items():
    file=root/f"data/mlb/game-results/{year}.json"
    if not file.is_file():bad.append(f"{year}: missing");continue
    actual=hashlib.sha256(file.read_bytes()).hexdigest()
    if actual!=digest:bad.append(f"{year}: checksum changed")
print(f"Checked {len(expected)} frozen MLB season files")
if bad:
    print("FROZEN HISTORY VIOLATION:",*bad,sep="\n")
    sys.exit(1)
print("Frozen MLB history matches approved manifest")
