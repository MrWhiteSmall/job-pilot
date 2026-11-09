"""Company list probe that tolerates slow sub-resources (wait_until='commit')."""

import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from browser_adapter import BossBrowser  # noqa: E402

browser = BossBrowser()
page = browser._new_page()
try:
    page.goto('https://www.zhipin.com/gongsi/', wait_until='commit', timeout=40000)
    page.wait_for_timeout(6000)
    print('landed:', page.url[:100], '| title:', page.title()[:40])
    for sel in ('.company-list', '.company-list li', 'a[href*="/gongsi/"]', '.company-info'):
        print(' ', sel, page.locator(sel).count())
    if page.locator('.company-list').count():
        html = re.sub(r'\s+', ' ', page.locator('.company-list').first.inner_html())
        print('html[:1800]:', html[:1800])
    for text in page.locator('.company-list li').all_inner_texts()[:4]:
        print('  card:', re.sub(r'\s+', ' ', text)[:120])
    page.screenshot(path=str(BASE / 'data' / 'screenshots' / 'company-list.png'), animations='disabled')
finally:
    browser._sweep(keep=0)
