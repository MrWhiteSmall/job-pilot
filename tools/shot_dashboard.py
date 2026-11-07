"""Screenshot the live dashboard list to confirm salary rendering."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r'D:\DesktopCode\job-pilot\data\screenshots')
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    page.goto('http://127.0.0.1:8765', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(1500)
    rows = page.locator('.job-row').count()
    samples = page.locator('.job-row .job-city').all_inner_texts()[:6]
    page.screenshot(path=str(OUT / 'dashboard-salary.png'), full_page=False)
    print('rows', rows)
    print('\n'.join(samples))
    browser.close()
