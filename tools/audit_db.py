"""Audit the local database for mis-screened jobs (false negatives and false positives).

Reads data/job_pilot.sqlite3, re-runs the *current* rules against every job, and prints:
  1. jobs still rejected whose title clearly looks like a dev/AI role  -> possible false negatives
  2. jobs still rejected for "social/campus" or "education"            -> phrasing problems
  3. jobs already sent that today's rules would reject                 -> false positives
  4. salary strings the parser cannot read                              -> data quality
  5. company-size coverage                                              -> why so many "待核验"

Usage: python tools/audit_db.py [--json]
Writes nothing except an optional markdown report to data/audit-db.md.
"""

import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from engine import JobEngine  # noqa: E402

DB = Path(os.getenv('JOB_PILOT_DB', str(BASE / 'data' / 'job_pilot.sqlite3')))
engine = JobEngine(str(DB))
rules = engine.get_rules()['data']
resume = engine.get_profile().get('resume_text', '')

DEV_WORDS = ('ai', 'agent', '智能体', '大模型', '模型', '算法', 'python', '后端', '服务端',
             '全栈', '开发', '研发', '工程师', '架构', 'rag', 'llm', 'nlp', '多模态')

conn = sqlite3.connect(str(DB))
rows = conn.execute('SELECT id, score, reason, status, data FROM jobs ORDER BY id').fetchall()

rejected_but_dev = []
rejected_social = []
rejected_education = []
sent_but_rejected = []
salary_odd = []
size_missing = 0
titles = Counter()

for jid, score, reason, status, data in rows:
    job = json.loads(data)
    title = str(job.get('title', ''))
    titles[(title, job.get('company', ''))] += 1
    new_score, new_reason = engine.match_job(job, resume, rules)
    if not job.get('company_size'):
        size_missing += 1
    salary = str(job.get('salary', '')).strip()
    if salary and (any(x in salary for x in ('元/天', '元/时', '万', '面议')) or not any(c.isdigit() for c in salary)):
        salary_odd.append((jid, title, salary))
    if new_score < 0:
        looks_dev = any(w in title.lower() for w in DEV_WORDS)
        if status == 'sent':
            sent_but_rejected.append((jid, title, job.get('company'), new_reason, salary))
        elif looks_dev and '职位不符合规则' in new_reason:
            rejected_but_dev.append((jid, title, job.get('company'), salary))
        elif looks_dev and '社会招聘' in new_reason:
            rejected_social.append((jid, title, job.get('company'), job.get('experience'), job.get('recruitment_type')))
        elif looks_dev and '学历' in new_reason:
            rejected_education.append((jid, title, job.get('company'), job.get('education')))

print(f'总数 {len(rows)} | 公司规模缺失 {size_missing} ({size_missing * 100 // max(1, len(rows))}%)')
print(f'重复标题+公司 {sum(1 for v in titles.values() if v > 1)} 组')

print(f'\n== A. 标题像研发/算法，但被「职位不符合规则」拒掉：{len(rejected_but_dev)} ==')
for row in rejected_but_dev[:20]:
    print('  ', row)

print(f'\n== B. 标题像研发，但被判「仅限社招/校招」：{len(rejected_social)} ==')
for row in rejected_social[:20]:
    print('  ', row)

print(f'\n== C. 标题像研发，但被判学历超标：{len(rejected_education)} ==')
for row in rejected_education[:15]:
    print('  ', row)

print(f'\n== D. 已经投出去、但按今天规则会被拒（规则漂移）：{len(sent_but_rejected)} ==')
for row in sent_but_rejected[:25]:
    print('  ', row)

print(f'\n== E. 薪资字符串读不出（面议/元天/万）：{len(salary_odd)} ==')
for row in salary_odd[:15]:
    print('  ', row)

reason_now = Counter(engine.match_job(json.loads(d), resume, rules)[1].split('；')[0] for _, _, _, _, d in rows)
print('\n== F. 用当前规则重算的拒绝原因分布 ==')
for reason, count in reason_now.most_common(12):
    print(f'  {count:>4}  {reason}')
