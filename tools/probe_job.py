"""Open one BOSS job page and dump what the apply buttons actually look like.

    python tools/probe_job.py <job_url>

Does NOT close the shared Chrome (the app is using it).
"""

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from browser_adapter import BossBrowser  # noqa: E402

url = sys.argv[1] if len(sys.argv) > 1 else 'https://www.zhipin.com/job_detail/8bf5f07733934dc80nNy09i-FlRR.html'
browser = BossBrowser()

page = browser._new_page()
try:
    browser._goto(page, url, timeout=25000)
    print('url   =', page.url)
    print('title =', page.title())
    body = page.inner_text('body')
    print('body  =', body[:500].replace('\n', ' | '))
    for selector in ('a', 'button', 'span', 'div'):
        try:
            nodes = page.locator(selector).all()
        except Exception:
            continue
        hits = []
        for node in nodes[:400]:
            try:
                text = (node.inner_text() or '').strip()
            except Exception:
                continue
            if text and any(word in text for word in ('沟通', '投递', '简历', '已')):
                if len(text) <= 12:
                    hits.append(text)
        if hits:
            from collections import Counter
            print(f'{selector:7}', Counter(hits).most_common(8))
    page.screenshot(path=str(BASE / 'data' / 'screenshots' / 'job-probe.png'), animations='disabled')
    print('screenshot -> data/screenshots/job-probe.png')
finally:
    browser._sweep(keep=0)
