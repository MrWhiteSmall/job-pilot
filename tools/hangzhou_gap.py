import json
import re
import sys
import collections
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import JobEngine

BASE = Path(__file__).resolve().parent.parent
e = JobEngine(str(BASE / 'data' / 'job_pilot.sqlite3'))
rules = e.get_rules()['data']
resume = e.get_profile()['resume_text']
contacted = e.contacted_companies()

with e._connect() as conn:
    rows = [dict(r) for r in conn.execute("SELECT * FROM jobs").fetchall()]

hz = []
for r in rows:
    data = json.loads(r['data'])
    if '杭州' in str(data.get('city') or ''):
        r['data'] = data
        hz.append(r)

# 1) 只被公司去重挡住、其余条件都过的岗位
blocked_ok = []
for r in hz:
    if r['status'] not in ('matched', 'approved', 'sent', 'blocked', 'uncertain'):
        continue
    if e._company_key(r['data'].get('company')) not in contacted:
        continue
    score, reason = e.match_job(r['data'], resume, rules)
    if score >= 40:
        blocked_ok.append((r['id'], score, r['status'], str(r['data'].get('title'))[:28], str(r['data'].get('company'))[:18]))
print('=== 只因「同公司已沟通」被挡的岗位:', len(blocked_ok))
for row in blocked_ok[:12]:
    print('  ', row)

# 2) 放宽标题关键词后能救回多少被拒岗位
loose = dict(rules)
loose['titles'] = list(rules.get('titles') or []) + ['研发', '应用', '平台', '数据', '架构']
recovered = []
for r in hz:
    if r['status'] != 'rejected':
        continue
    score, reason = e.match_job(r['data'], resume, loose)
    if score >= 0:
        recovered.append((r['id'], score, str(r['data'].get('title'))[:30], str(r['reason'])[:34]))
print('\n=== 放宽标题词后可救回:', len(recovered))
for row in recovered[:15]:
    print('  ', row)

# 3) 放宽 exclude_titles（去掉 研究员/架构师/负责人）后能救回多少
loose2 = dict(loose)
loose2['exclude_titles'] = [x for x in (rules.get('exclude_titles') or [])
                            if x not in ('研究员', '架构师', '负责人', '总监', '主管')]
recovered2 = []
for r in hz:
    if r['status'] != 'rejected':
        continue
    score, reason = e.match_job(r['data'], resume, loose2)
    if score >= 0:
        recovered2.append((r['id'], score, str(r['data'].get('title'))[:30], str(r['reason'])[:30]))
print('\n=== 再去掉职级排除后可救回:', len(recovered2))
for row in recovered2[:12]:
    print('  ', row)

# 4) 已被拒但标题含明显研发词、且原因不是算法/职级
miss = [r for r in hz if r['status'] == 'rejected'
        and re.search('开发|工程师|研发', str(r['data'].get('title') or ''))
        and '职位不符合' in str(r['reason'] or '')]
print('\n=== 标题含研发词但「职位不符合规则」:', len(miss))
for r in miss[:15]:
    print('  ', r['id'], str(r['data'].get('title'))[:32], '|', str(r['data'].get('salary'))[:10])
