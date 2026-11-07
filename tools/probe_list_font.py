"""Inspect salary text on BOSS search cards: codepoints, font family, and font resources."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from browser_adapter import BossBrowser  # noqa: E402

OUT = ROOT / 'data' / 'fonts'
OUT.mkdir(parents=True, exist_ok=True)

browser = BossBrowser()
try:
    page = browser._new_page()
    browser._goto(page, 'https://www.zhipin.com/web/geek/jobs?city=101210100&query=AI', timeout=25000)
    try:
        page.wait_for_selector('.job-card-wrapper, .job-card-box', timeout=20000)
    except Exception as exc:
        print('cards never appeared:', str(exc)[:80], page.url)
    page.wait_for_timeout(2500)
    info = page.evaluate("""() => {
      const cards = Array.from(document.querySelectorAll('.job-card-box, .job-card-wrapper')).slice(0, 3);
      const out = cards.map(c => {
        const s = c.querySelector('.salary, .job-salary');
        if (!s) return null;
        const cs = getComputedStyle(s);
        return {text: s.textContent.trim(), codes: Array.from(s.textContent.trim()).map(ch => ch.codePointAt(0).toString(16)),
                family: cs.fontFamily, weight: cs.fontWeight};
      });
      return {cards: out.filter(Boolean),
              fonts: performance.getEntriesByType('resource').map(e => e.name).filter(n => /font|\\.woff2?|\\.ttf/i.test(n)).slice(0, 12)};
    }""")
    print(json.dumps(info, ensure_ascii=False)[:1500])
    for i, link in enumerate(info['fonts']):
        suffix = Path(link.split('?')[0]).suffix or '.bin'
        try:
            import urllib.request
            req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.zhipin.com/'})
            data = urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=25).read()
            (OUT / f'list-font-{i}{suffix}').write_bytes(data)
            print('saved', i, suffix, len(data))
        except Exception as exc:
            print('failed', i, exc)
finally:
    browser.close()
