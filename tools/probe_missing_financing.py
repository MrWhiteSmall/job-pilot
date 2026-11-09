"""Probe a 0-20 浜?job that still has no financing info and print the raw company blocks."""

import json
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from browser_adapter import browser  # noqa: E402

conn = sqlite3.connect(str(BASE / 'data' / 'job_pilot.sqlite3'))
target = None
for jid, data in conn.execute("SELECT id, data FROM jobs"):
    job = json.loads(data)
    if str(job.get('company_size') or '').startswith('0-20') and not job.get('financing'):
        target = (jid, job)
        break

jid, job = target
print(jid, job.get('title'), '@', job.get('company'), job.get('company_size'))

page = browser._new_page()
try:
    browser._goto(page, job['url'], timeout=25000)
    browser._check(page)
    for selector in ('.sider-company', '.job-company', '.company-info', '.company-info-box', '.company-detail'):
        nodes = page.locator(selector)
        count = nodes.count()
        print(f'--- {selector} count={count}')
        for index in range(min(count, 2)):
            print(repr(nodes.nth(index).inner_text()[:300]))
    body = page.inner_text('body')
    for word in ('铻嶈祫', '鏈瀺璧?, '涓嶉渶瑕佽瀺璧?, '澶╀娇杞?, '杞?):
        index = body.find(word)
        if index >= 0:
            print('BODY around', word, ':', repr(body[max(0, index - 60):index + 60]))
finally:
    browser._sweep(keep=0)
    # 不要关共享浏览器

