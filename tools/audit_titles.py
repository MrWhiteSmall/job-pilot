"""Group the '职位不符合规则' rejects so the user can decide which titles should be in scope."""

import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from engine import JobEngine  # noqa: E402

engine = JobEngine(str(BASE / 'data' / 'job_pilot.sqlite3'))
rules = engine.get_rules()['data']
resume = engine.get_profile().get('resume_text', '')
conn = sqlite3.connect(str(BASE / 'data' / 'job_pilot.sqlite3'))

ALGO = ('算法', '视觉', '图像', '具身', '仿真', '强化学习', '感知', 'SLAM', '运控', '决策规划', 'NLP', '语音')
ENG = ('后端', '服务端', 'python', 'java', 'go', '引擎', '平台', '架构', '研发', '开发', '全栈', '数据')

groups = defaultdict(list)
for jid, data, reason in conn.execute("SELECT id, data, reason FROM jobs WHERE status='rejected'"):
    job = json.loads(data)
    score, why = engine.match_job(job, resume, rules)
    if score >= 0 or not why.startswith('职位不符合'):
        continue
    title = job.get('title', '')
    low = title.lower()
    if any(k.lower() in low for k in ALGO):
        groups['算法/研究类（图像·具身·仿真·NLP）'].append((jid, title, job.get('company'), job.get('salary')))
    elif any(k in low for k in ENG):
        groups['工程类（后端/Python/引擎/平台，可能误杀）'].append((jid, title, job.get('company'), job.get('salary')))
    else:
        groups['其他'].append((jid, title, job.get('company'), job.get('salary')))

for name, rows in groups.items():
    print(f'## {name}  {len(rows)} 条')
    for jid, title, company, salary in rows[:20]:
        print(f'   {jid:>5} {title[:30]:<32} {str(company)[:18]:<20} {salary}')
