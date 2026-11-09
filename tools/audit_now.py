"""一次性体检：筛得对不对、检索够不够、重复还剩多少。

    python tools/audit_now.py
"""

import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from engine import JobEngine  # noqa: E402

DB = Path(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
ENGINE = JobEngine(str(DB))
RULES = ENGINE.get_rules()['data']
RESUME = (ENGINE.get_profile() or {}).get('resume_text') or ''

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = [dict(r) for r in conn.execute('SELECT * FROM jobs ORDER BY id')]
for row in rows:
    row['data'] = json.loads(row['data'] or '{}')
    row['analysis'] = json.loads(row['analysis']) if row['analysis'] else None

print('=== 总量')
print('jobs', len(rows), Counter(r['status'] for r in rows))
print('companies', len({r['data'].get('company') for r in rows}))

print('\n=== 拒绝原因 Top12')
reasons = Counter()
for r in rows:
    if r['status'] == 'rejected':
        reasons[(r['reason'] or '')[:28]] += 1
for reason, count in reasons.most_common(12):
    print(f'{count:4d}  {reason}')

print('\n=== 疑似误杀：标题像研发但被判「职位不符合/非研发岗」')
DEV = re.compile(r'(AI|大模型|LLM|Agent|智能体|全栈|后端|Python|算法|数据|平台|研发|开发|架构)', re.I)
bad = [r for r in rows if r['status'] == 'rejected'
       and ('职位不符合' in (r['reason'] or '') or '非研发' in (r['reason'] or ''))
       and DEV.search(r['data'].get('title', ''))]
for r in bad:
    print(f"  {r['id']:5d} {r['data'].get('title','')[:30]} @ {r['data'].get('company','')[:14]} | {r['reason'][:40]}")
print('  subtotal', len(bad))

print('\n=== 已沟通但按现在规则会被拒（规则漂移）')
drift = []
for r in rows:
    if r['status'] != 'sent':
        continue
    score, reason = JobEngine.match_job(r['data'], RESUME, RULES)
    if score < 0:
        drift.append((r['id'], r['data'].get('title', ''), r['data'].get('company', ''), reason))
for item in drift:
    print('  ', item[0], item[1][:26], '@', item[2][:12], '|', item[3][:40])
print('  subtotal', len(drift))

print('\n=== 重复')
urls = Counter(r['data'].get('url') for r in rows)
print('  同 URL 重复:', sum(1 for url, c in urls.items() if c > 1))
pairs = Counter((r['data'].get('company'), r['data'].get('title')) for r in rows)
print('  同公司同标题 重复组:', sum(1 for _, c in pairs.items() if c > 1))
sent_pairs = Counter((r['data'].get('company'), r['data'].get('title')) for r in rows if r['status'] == 'sent')
print('  已沟通里 同公司同标题:', [k for k, c in sent_pairs.items() if c > 1][:5])
sent_company = Counter(r['data'].get('company') for r in rows if r['status'] == 'sent')
print('  已沟通里 同公司多条:', sum(1 for _, c in sent_company.items() if c > 1))

print('\n=== 检索质量')
with_salary = sum(1 for r in rows if r['data'].get('salary'))
full_jd = sum(1 for r in rows if '【列表摘要' not in str(r['data'].get('description', '')))
print(f'  有薪资 {with_salary}/{len(rows)}；完整 JD {full_jd}/{len(rows)}')
print('  城市', Counter((r['data'].get('city') or '?')[:6] for r in rows).most_common(6))
print('  公司规模已知', sum(1 for r in rows if r['data'].get('company_size')), '/', len(rows))

print('\n=== 队列里的候选（matched/approved）')
queue = [r for r in rows if r['status'] in ('matched', 'approved')]
for r in sorted(queue, key=lambda x: -(x['score'] or 0))[:12]:
    d = r['data']
    print(f"  {r['id']:5d} {r['score']:3.0f} {d.get('title','')[:26]} @ {d.get('company','')[:12]} | {d.get('city','')[:8]} {d.get('salary','')} | {d.get('company_size','')}")
