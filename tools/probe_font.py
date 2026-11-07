"""Download the web font BOSS uses for salary digits and inspect its cmap."""
import json
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from browser_adapter import BossBrowser  # noqa: E402

OUT = ROOT / 'data' / 'fonts'
OUT.mkdir(parents=True, exist_ok=True)

db = sqlite3.connect(str(ROOT / 'data' / 'job_pilot.sqlite3'))
row = db.execute("SELECT data FROM jobs WHERE status='sent' ORDER BY id DESC LIMIT 1").fetchone()
url = json.loads(row[0]).get('url')

browser = BossBrowser()
try:
    page = browser._new_page()
    browser._goto(page, url, timeout=25000)
    page.wait_for_timeout(1500)
    info = page.evaluate("""() => ({
      fonts: performance.getEntriesByType('resource').map(e => e.name).filter(n => /\\.(woff2?|ttf|otf)(\\?|$)/i.test(n)),
      salary: (() => { const el = document.querySelector('.job-banner .salary, .job-primary .salary, .salary'); return el ? {text: el.textContent.trim(), cls: el.className, html: el.outerHTML.slice(0,200)} : null; })(),
      faces: (() => { const out = []; for (const s of document.styleSheets) { try { for (const r of s.cssRules) if (r.cssText && r.cssText.includes('@font-face')) out.push(r.cssText.slice(0,300)); } catch (e) {} } return out; })()
    })""")
    print(json.dumps({k: info[k] for k in ('salary', 'faces')}, ensure_ascii=False)[:1200])
    print('font urls:', len(info['fonts']))
    for i, link in enumerate(info['fonts'][:6]):
        name = OUT / (f'boss-font-{i}' + Path(link.split('?')[0]).suffix)
        try:
            req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.zhipin.com/'})
            data = urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=25).read()
            name.write_bytes(data)
            print('saved', name.name, len(data))
        except Exception as exc:
            print('failed', link[:80], exc)
finally:
    browser.close()
