"""Dump a BOSS company page's job-list markup (run while the app is stopped)."""

import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from browser_adapter import BossBrowser  # noqa: E402

URL = sys.argv[1] if len(sys.argv) > 1 else 'https://www.zhipin.com/gongsi/99fc776f746341c103N609m9.html'

browser = BossBrowser()
page = browser._new_page()
try:
    page.goto(URL, wait_until='commit', timeout=40000)
    page.wait_for_timeout(4000)
    print('landed:', page.url[:100], '| title:', page.title()[:50])
    for sel in ('.job-list', '.job-list-box', '.job-card-wrapper', '.job-card-box',
                'a[href*="/job_detail/"]', '.job-name', '.job-salary', '.salary'):
        print(' ', sel, page.locator(sel).count())
    body = page.inner_text('body')
    print('body[:300]:', body[:300].replace('\n', ' | '))
    if page.locator('.job-list-box, .job-list').count():
        html = re.sub(r'\s+', ' ', page.locator('.job-list-box, .job-list').first.inner_html())
        print('html[:1800]:', html[:1800])
    page.screenshot(path=str(BASE / 'data' / 'screenshots' / 'company-page.png'), animations='disabled')
finally:
    browser.close()
