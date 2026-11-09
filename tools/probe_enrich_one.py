"""Run the production enrich() on a single job and print what came back."""

import json
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from browser_adapter import browser  # noqa: E402

conn = sqlite3.connect(str(BASE / 'data' / 'job_pilot.sqlite3'))
row = conn.execute("SELECT data FROM jobs WHERE id=9").fetchone()
job = json.loads(row[0])
item = {key: job.get(key, '') for key in ('title', 'company', 'city', 'salary', 'description', 'url', 'source',
                                         'company_size', 'education', 'experience', 'recruitment_type')}
print('in :', {k: item[k] for k in ('company_size', 'salary')})

done = browser.enrich([item], 1)
out = done[0]
print('out:', {k: out.get(k) for k in ('company_size', 'financing', 'company_type', 'salary', 'error')})
# 不要关共享浏览器

