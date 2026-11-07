"""Repair rows whose campus flag came from soft phrasing such as 接受应届."""
import json
import re
import sqlite3

DB = r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3'
db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
fixed = []
for row in db.execute('SELECT id, data FROM jobs').fetchall():
    data = json.loads(row['data'])
    if str(data.get('recruitment_type') or '') != 'campus':
        continue
    title = str(data.get('title') or '')
    stripped = re.sub(r'(接受|欢迎|允许|不限|均可)\s*应届', '', title)
    if stripped == title:
        continue
    data['recruitment_type'] = 'social'
    db.execute('UPDATE jobs SET data=?, status=?, score=NULL, reason=NULL WHERE id=?',
               (json.dumps(data, ensure_ascii=False), 'new', row['id']))
    fixed.append((row['id'], title))
db.commit()
print('fixed', len(fixed), fixed[:10])
