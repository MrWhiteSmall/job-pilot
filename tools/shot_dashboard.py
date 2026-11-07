"""Screenshot the running dashboard (desktop + mobile) into data/screenshots/.

Usage: start `python app.py`, then `python tools/shot_dashboard.py`.
"""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / 'data' / 'screenshots'
OUT.mkdir(parents=True, exist_ok=True)
URL = os.getenv('JOB_PILOT_URL', 'http://127.0.0.1:' + os.getenv('JOB_PILOT_PORT', '8765'))

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    for name, viewport in (('dashboard', {'width': 1440, 'height': 1000}),
                           ('dashboard-mobile', {'width': 390, 'height': 844})):
        page = browser.new_page(viewport=viewport)
        page.goto(URL, wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / f'{name}.png'), full_page=False)
        print(name, page.locator('.job-row').count(), 'rows')
        page.close()
    browser.close()
print('saved to', OUT)
