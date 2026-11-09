"""Inspect BOSS company listing DOM: which route really lists companies."""

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from browser_adapter import BossBrowser  # noqa: E402

URLS = [
    'https://www.zhipin.com/web/geek/company?city=101210100&scale=303,304',
    'https://www.zhipin.com/gongsi/',
]
SELECTORS = ['a[href*="/gongsi/"]', 'a[href*="/job_detail/"]', '.company-card', '.company-item',
             '.brand', '.brand-item', '.company-list', '.card-area', '.company-box']

browser = BossBrowser()
page = browser._new_page()
try:
    for url in URLS:
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(3000)
            body = page.inner_text('body')
            print('===', url)
            print('landed:', page.url[:100], '| title:', page.title()[:40])
            print('body:', body[:200].replace('\n', ' | '))
            for sel in SELECTORS:
                print(' ', sel, page.locator(sel).count())
            links = page.locator('a[href*="/gongsi/"]')
            for i in range(min(3, links.count())):
                print('   link:', (links.nth(i).inner_text() or '').strip()[:20], links.nth(i).get_attribute('href'))
            page.screenshot(path=str(BASE / 'data' / 'screenshots' / 'company-page.png'), animations='disabled')
        except Exception as exc:
            print('===', url, 'FAILED', str(exc).splitlines()[0][:100])
finally:
    browser._sweep(keep=0)
