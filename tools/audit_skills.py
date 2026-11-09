import json
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from engine import JobEngine  # noqa: E402

engine = JobEngine(str(BASE / 'data' / 'job_pilot.sqlite3'))
rules = engine.get_rules()['data']
resume = engine.get_profile().get('resume_text', '')
conn = sqlite3.connect(str(BASE / 'data' / 'job_pilot.sqlite3'))

count = 0
for jid, data in conn.execute("SELECT id, data FROM jobs WHERE status='rejected'"):
    job = json.loads(data)
    score, why = engine.match_job(job, resume, rules)
    if score < 0 and ('技能' in why or '证据' in why):
        count += 1
        print(jid, '|', job.get('title'), '@', job.get('company'), '|', job.get('salary'), '|', why)
print('count', count)
