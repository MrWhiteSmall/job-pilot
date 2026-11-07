import json
import sqlite3

db = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
db.row_factory = sqlite3.Row
ids = [664, 667, 675, 665]
for jid in ids:
    r = db.execute('SELECT * FROM jobs WHERE id=?', (jid,)).fetchone()
    d = json.loads(r['data'])
    print(jid, '|', d.get('title'), '|', d.get('company'), '|reason:', (r['reason'] or '')[:80])
    print('   exp:', d.get('experience'), '| type:', d.get('recruitment_type'), '| edu:', d.get('education'))
    print('   JD:', (d.get('description') or '')[:220].replace('\n', ' '))
print('---- remaining 职位不符 ----')
for r in db.execute("SELECT * FROM jobs WHERE status='rejected'"):
    if (r['reason'] or '').startswith('职位不符合规则'):
        d = json.loads(r['data'])
        print(r['id'], d.get('title'), '|', d.get('company'))
