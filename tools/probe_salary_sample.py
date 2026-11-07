"""Sample a few job pages and report how often salary text is readable."""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from browser_adapter import BossBrowser  # noqa: E402

PUA = re.compile('[\ue000-\uf8ff]')
db = sqlite3.connect(str(ROOT / 'data' / 'job_pilot.sqlite3'))
rows = [json.loads(r[0]) for r in db.execute('SELECT data FROM jobs ORDER BY id DESC LIMIT 40')]
targets = [r for r in rows if not str(r.get('salary') or '').strip()][:6]

browser = BossBrowser()
try:
    page = browser._new_page()
    for job in targets:
        try:
            browser._goto(page, job['url'], timeout=25000)
            page.wait_for_timeout(1200)
            text = page.evaluate("""() => {
              const el = document.querySelector('.job-banner .salary, .job-primary .salary, .salary, [class*=salary]');
              return el ? {text: el.textContent.trim(), family: getComputedStyle(el).fontFamily} : null;
            }""")
            print(json.dumps({'title': job['title'][:14], 'salary': text, 'pua': bool(PUA.search((text or {}).get('text', '')))}, ensure_ascii=False))
        except Exception as exc:
            print('error', job['url'][-24:], str(exc)[:80])
finally:
    browser.close()
