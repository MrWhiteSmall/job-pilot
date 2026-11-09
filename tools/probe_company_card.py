"""Dump the company block of one 0-20 浜?job page to see whether 铻嶈祫闃舵 is exposed."""

import json
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from browser_adapter import browser  # noqa: E402

conn = sqlite3.connect(str(BASE / 'data' / 'job_pilot.sqlite3'))
url = None
for (data,) in conn.execute("SELECT data FROM jobs WHERE status != 'sent'"):
    job = json.loads(data)
    if str(job.get('company_size') or '').startswith('0-20'):
        url = job['url']
        print(job.get('title'), '@', job.get('company'), job.get('company_size'))
        break

page = browser._new_page()
try:
    browser._goto(page, url, timeout=25000)
    browser._check(page)
    for selector in ('.job-banner', '.sider-company', '.company-info', '.job-company', '.job-detail-company'):
        nodes = page.locator(selector)
        if nodes.count():
            text = nodes.first.inner_text()
            print(f'--- {selector} ---')
            print(text[:600])
finally:
    browser._sweep(keep=0)
    # 不要关共享浏览器：那是 app 正在用的同一个 Chrome

