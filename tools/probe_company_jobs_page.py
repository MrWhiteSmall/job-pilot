"""Dump the /gongsi/job/<id>.html listing markup."""

import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from browser_adapter import BossBrowser  # noqa: E402

URL = sys.argv[1] if len(sys.argv) > 1 else 'https://www.zhipin.com/gongsi/job/99fc776f746341c103N609m9.html'

browser = BossBrowser()
page = browser._new_page()
try:
    page.goto(URL, wait_until='commit', timeout=40000)
    page.wait_for_timeout(4000)
    print('landed:', page.url[:100], '| title:', page.title()[:50])
    for sel in ('.job-list-box', '.job-card-wrapper', '.job-card-box', '.job-card-body',
                'a[href*="/job_detail/"]', '.job-name', '.salary', '.job-area'):
        print(' ', sel, page.locator(sel).count())
    if page.locator('.job-list-box').count():
        html = re.sub(r'\s+', ' ', page.locator('.job-list-box').first.inner_html())
        print('html[:1400]:', html[:1400])
    page.screenshot(path=str(BASE / 'data' / 'screenshots' / 'company-jobs.png'), animations='disabled')
finally:
    browser.close()
