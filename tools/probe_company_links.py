"""Print the '查看全部职位' link and hot-job anchors on a BOSS company page."""

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
    for anchor in page.locator('a').all()[:120]:
        try:
            text = (anchor.inner_text() or '').strip()
            href = anchor.get_attribute('href') or ''
        except Exception:
            continue
        if '职位' in text or '/job_detail/' in href:
            print(repr(text[:24]), '->', href[:90])
finally:
    browser.close()
