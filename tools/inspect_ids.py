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

for jid in (1060, 1750, 665, 675, 676, 1168, 712):
    row = conn.execute('SELECT status, data FROM jobs WHERE id=?', (jid,)).fetchone()
    if not row:
        print(jid, 'missing')
        continue
    job = json.loads(row[1])
    print(f'--- {jid} [{row[0]}] {job.get("title")} @ {job.get("company")}')
    print('    exp=%r type=%r edu=%r size=%r city=%r salary=%r' % (
        job.get('experience'), job.get('recruitment_type'), job.get('education'),
        job.get('company_size'), job.get('city'), job.get('salary')))
    print('    socal=', engine._social_job(job), 'match=', engine.match_job(job, resume, rules))
