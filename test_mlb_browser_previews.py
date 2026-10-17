#!/usr/bin/env python3
"""Chromium smoke tests for nonpublished MLB HTML previews."""
import json
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    root=Path("mlb/data/html-preview").resolve()
    handler=partial(SimpleHTTPRequestHandler,directory=str(root))
    server=ThreadingHTTPServer(("127.0.0.1",0),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    results=[]
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            try:
                for slug in ("atlanta-braves","chicago-cubs","detroit-tigers"):
                    page=browser.new_page(viewport={"width":1360,"height":900})
                    page.goto(f"http://127.0.0.1:{server.server_port}/mlb/teams/{slug}/index.html",wait_until="domcontentloaded")
                    page.locator("#wiseSeasonSelect").select_option("2020")
                    rows=page.locator("#schedule tbody tr")
                    assert rows.count()==12,(slug,rows.count())
                    button=page.locator("#wiseMoreGames")
                    assert button.count()==1,slug
                    button.click()
                    count=rows.count()
                    assert count in (58,60),(slug,count)
                    assert "undefined" not in page.locator("#schedule").inner_text().lower(),slug
                    page.locator("#wiseSeasonSelect").select_option("2025")
                    assert page.locator("#schedule tbody tr").count()==12,slug
                    results.append({"team":slug,"2020_rows_after_expansion":count,"2025_first_page_rows":12})
                    page.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
    print(json.dumps({"status":"BROWSER_SMOKE_PASS","teams":results,"published":False}))
if __name__=="__main__":main()
