"""Targeted checks for the screening audit: blacklist hits, size rejects, soft-campus wording."""

import json
import sqlite3
from collections import Counter
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from engine import JobEngine  # noqa: E402

DB = BASE / 'data' / 'job_pilot.sqlite3'
engine = JobEngine(str(DB))
rules = engine.get_rules()['data']
resume = engine.get_profile().get('resume_text', '')

conn = sqlite3.connect(str(DB))
rows = conn.execute('SELECT id, status, data FROM jobs ORDER BY id').fetchall()

black_hits, size_hits, soft = [], [], []
for jid, status, data in rows:
    job = json.loads(data)
    score, reason = engine.match_job(job, resume, rules)
    if score >= 0:
        continue
    company = str(job.get('company', ''))
    title = str(job.get('title', ''))
    if '命中黑名单' in reason:
        hit = [b for b in rules.get('blacklist', []) if b.lower() in (title + ' ' + company).lower()]
        black_hits.append((company, hit))
    elif '公司规模' in reason:
        size_hits.append((job.get('company_size'), company))
    elif '社会招聘' in reason and any(w in title for w in ('AI', 'Agent', '大模型', '算法', 'Python', '开发')):
        soft.append((jid, title, company, job.get('experience'), job.get('recruitment_type'),
                     '校招' in title, str(job.get('description', ''))[:60]))

print('== 黑名单命中（按公司去重，看有没有误伤小公司）==')
for company, hit in Counter(c for c, _ in black_hits).most_common(40):
    hits = [h for c, h in black_hits if c == company][0]
    print(f'  {company!r:<46} via {hits}')

print('\n== 公司规模拒绝（按规模值统计）==')
for size, count in Counter(s for s, _ in size_hits).most_common(12):
    print(f'  {size!r:<18} x{count}')

print('\n== 疑似软性校招措辞（标题/经验 containing 校招/应届）==')
for row in soft[:20]:
    print('  ', row)
