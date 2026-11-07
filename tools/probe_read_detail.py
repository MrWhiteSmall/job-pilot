"""Read one job detail through the adapter and print the facts it extracted."""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from browser_adapter import BossBrowser  # noqa: E402

db = sqlite3.connect(str(ROOT / 'data' / 'job_pilot.sqlite3'))
rows = [json.loads(r[0]) for r in db.execute('SELECT data FROM jobs ORDER BY id DESC LIMIT 60')]
target = [r for r in rows if not str(r.get('salary') or '').strip()][0]
print('before:', {k: target.get(k) for k in ('title', 'company', 'salary', 'company_size')})

browser = BossBrowser()
try:
    page = browser._new_page()
    item = browser._read_detail(page, dict(target))
    print('after :', {k: item.get(k) for k in ('title', 'company', 'salary', 'company_size', 'education', 'experience')})
    print('raw salary text:', page.evaluate("() => { const el = document.querySelector('.salary'); return el ? el.outerHTML : null; }"))
finally:
    browser.close()
