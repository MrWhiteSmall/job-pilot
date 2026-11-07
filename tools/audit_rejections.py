"""Audit rejected jobs: recompute the firing rule and explain it, flag likely false kills."""
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import engine as eng

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'data' / 'job_pilot.sqlite3'

core = eng.JobEngine.__dict__
db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
rows = db.execute('SELECT * FROM jobs').fetchall()
row = db.execute('SELECT data FROM rules ORDER BY id DESC LIMIT 1').fetchone()
rules = json.loads(row['data']) if row and row['data'] else {}
resume_row = db.execute('SELECT resume_text FROM profile ORDER BY id DESC LIMIT 1').fetchone()
resume = resume_row['resume_text'] if resume_row else ''

jobs = []
for r in rows:
    data = json.loads(r['data'])
    data['id'] = r['id']
    data['status'] = r['status']
    data['score'] = r['score']
    data['reason'] = r['reason']
    jobs.append(data)

blacklist = rules.get('blacklist', [])
titles_kw = rules.get('titles', [])
exclude_kw = rules.get('exclude_titles', [])

groups = defaultdict(list)
flags = []
for job in jobs:
    if job['status'] != 'rejected':
        continue
    reason = job.get('reason') or ''
    key = reason.split('：')[0]
    detail = {}
    title = str(job.get('title') or '').lower()
    company = str(job.get('company') or '')
    text = (title + ' ' + company.lower())
    band = eng.JobEngine._company_band(job.get('company_size'))
    if key == '命中黑名单':
        hit = [x for x in blacklist if x.lower() in text]
        detail['命中词'] = hit
        if hit and min(len(x) for x in hit) <= 2:
            flags.append((job, '黑名单命中词过短：' + '/'.join(hit)))
    elif key in ('职位不符合规则',):
        detail['未命中关键词'] = [x for x in titles_kw if x.lower() not in title][:6]
        if re.search(r'ai|算法|大模型|llm|agent|智能体|开发|python|后端', title):
            flags.append((job, '标题看似研发岗却被职位规则刷掉'))
    elif key == '职位方向不符（非研发岗）':
        hit = [x for x in exclude_kw if x.lower() in title]
        detail['排除词'] = hit
        if re.search(r'ai|算法|大模型|llm|agent|智能体|开发|python|后端', title):
            flags.append((job, '标题含研发字样但命中高级/非研发排除词：' + '/'.join(hit)))
    elif key == '公司规模不符合规则':
        detail['规模'] = job.get('company_size')
        detail['解析区间'] = band
        if band and band[0] >= 100 and band[1] <= 1000:
            flags.append((job, f'规模 {job.get("company_size")} 解析为 {band} 却被拒'))
    elif key == '学历要求超过最高学历':
        detail['学历'] = job.get('education')
        detail['解析'] = eng.JobEngine._education_level(job.get('education'))
        if detail['解析'] and detail['解析'] <= 3:
            flags.append((job, f'学历 {detail["学历"]} 不应超过硕士上限'))
    elif key.startswith('仅限社会招聘'):
        detail['招聘类型'] = job.get('recruitment_type')
        detail['经验'] = job.get('experience')
        exp = str(job.get('experience') or '')
        if any(x in exp for x in ('1-3年', '3-5年', '5-10年', '10年以上', '经验不限')):
            flags.append((job, f'经验 {exp} 表明社招却被校园规则刷掉'))
    elif key == '城市不符合规则或城市缺失':
        detail['城市'] = job.get('city')
        if '杭州' in str(job.get('city') or ''):
            flags.append((job, '城市含杭州却被刷掉'))
    elif key.startswith('起薪'):
        detail['薪资'] = job.get('salary')
    groups[key].append((job, detail))

lines = ['# 筛选误杀审计', '', f'岗位总数 {len(jobs)}，被拒 {sum(len(v) for v in groups.values())}', '']
lines.append('## 拒绝原因分布')
for key, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    lines.append(f'- {key}: {len(items)}')

lines += ['', '## 可能误杀（%d 条）' % len(flags)]
for job, why in flags[:80]:
    lines.append(f'- #{job["id"]} {job["title"]} | {job["company"]} | {job.get("city")} | {job.get("salary")} | '
                 f'{job.get("company_size")} | {job.get("education")} | {job.get("experience")} → {why}')

lines += ['', '## 各原因抽样']
for key, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    lines += ['', f'### {key}（{len(items)} 条）']
    for job, detail in items[:8]:
        lines.append(f'- #{job["id"]} {job["title"]} | {job["company"]} | {job.get("city")} | {job.get("salary")} | '
                     f'{job.get("company_size")} | {job.get("education")} | {job.get("experience")} | {detail}')

out = ROOT / 'data' / 'audit-rejections.md'
out.write_text('\n'.join(lines), encoding='utf-8')
print('\n'.join(lines[:60]))
print('...')
print('full report:', out)
