"""Explicit read-only live collection verification; no employer contacts."""
import json
from pathlib import Path
from browser_adapter import browser
try:
    jobs = browser.collect({'titles': ['AI应用'], 'cities': ['杭州']})
    Path('data/boss-collected.json').write_text(json.dumps(jobs, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'count': len(jobs), 'examples': [{k:j[k] for k in ('title','company','city','salary')} for j in jobs[:3]]}, ensure_ascii=True))
finally:
    browser.close()
