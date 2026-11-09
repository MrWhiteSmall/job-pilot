"""Final audit numbers for the report: which rejections are defensible, which look wrong."""

import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from engine import JobEngine  # noqa: E402

engine = JobEngine(str(BASE / 'data' / 'job_pilot.sqlite3'))
rules = engine.get_rules()['data']
resume = engine.get_profile().get('resume_text', '')
conn = sqlite3.connect(str(BASE / 'data' / 'job_pilot.sqlite3'))

CAMPUS = ('应届', '在校', '校招', '校园', '实习')
rows = list(conn.execute('SELECT id, data, status, reason FROM jobs'))
print('total', len(rows), Counter(r[2] for r in rows))

# 1) campus tag but no campus wording anywhere -> tag-driven, not evidence-driven
tag_only = []
for jid, data, status, reason in rows:
    job = json.loads(data)
    if job.get('recruitment_type') != 'campus' or status == 'sent':
        continue
    text = (str(job.get('title', '')) + ' ' + str(job.get('experience', '')) + ' ' +
            str(job.get('description', ''))[:400])
    text = re.sub(r'(接受|欢迎|允许|不限|均可|可|也能|也要|同时)\s*(?:应届生?|校招生?|校园招聘)', '', text)
    if not any(word in text for word in CAMPUS):
        tag_only.append((jid, job.get('title'), job.get('company'), job.get('experience'), job.get('education')))
print('\n[1] 打 campus 标签但正文没有校招字样:', len(tag_only))
for item in tag_only[:15]:
    print('   ', item)

# 2) size-missing share among matched / rejected
size_missing = 0
for jid, data, status, reason in rows:
    job = json.loads(data)
    if not str(job.get('company_size') or '').strip():
        size_missing += 1
print('\n[2] 公司规模缺失:', size_missing, f'{size_missing / len(rows):.0%}')

# 3) how many rejects had *no* description (blind screening)
blind = 0
for jid, data, status, reason in rows:
    job = json.loads(data)
    if status == 'rejected' and '【列表摘要' in str(job.get('description', '')):
        blind += 1
print('[3] 仅凭列表摘要就被拒:', blind)

# 4) sent jobs that today's rules would reject
drift = []
for jid, data, status, reason in rows:
    if status != 'sent':
        continue
    job = json.loads(data)
    score, why = engine.match_job(job, resume, rules)
    if score < 0:
        drift.append((jid, job.get('title'), job.get('company'), why))
print('\n[4] 已沟通但按今天的规则会被拒:', len(drift))
for item in drift:
    print('   ', item)
