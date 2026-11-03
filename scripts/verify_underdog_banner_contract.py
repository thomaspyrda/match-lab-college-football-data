#!/usr/bin/env python3
"""Fail deployment if the shared banner can revert through stale navigation or sizing."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_JS = "site-navigation-v12.js?v=20261102-canonical-banner-v1"
CANONICAL_CSS = "assets/underdog-banner.css?v=20261102-canonical-v1"
css = (ROOT / "assets/underdog-banner.css").read_text(encoding="utf-8")
assert "aspect-ratio:1194/98!important" in css, "Desktop banner geometry changed"
assert "aspect-ratio:5.2/1!important" in css, "Mobile banner geometry changed"
assert "width:min(90vw,calc(100% - 24px))!important" in css, "Mobile banner width changed"

for version in ("v11", "v12"):
    nav = (ROOT / f"site-navigation-{version}.js").read_text(encoding="utf-8")
    assert CANONICAL_CSS in nav, f"{version}: canonical banner CSS not loaded"
    assert 'styleId = "underdog-hero-banner-style"' not in nav, f"{version}: legacy injected banner sizes exist"
    assert 'aspect-ratio:1194/98' not in nav, f"{version}: local banner sizing duplicated"

total = 0
for path in ROOT.rglob("*.html"):
    if any(part in {".git", "node_modules"} for part in path.relative_to(ROOT).parts):
        continue
    src = path.read_text(encoding="utf-8")
    if re.search(r'<nav\b[^>]*(?:class=["\'][^"\']*site-nav|aria-label=["\'](?:Primary|Mobile) navigation)', src, re.I):
        total += 1
        assert CANONICAL_JS in src, f"Non-canonical navigation script: {path}"
assert total > 50, f"Unexpectedly few checked sport pages: {total}"
print(f"Banner release guard passed for {total} sport pages")
