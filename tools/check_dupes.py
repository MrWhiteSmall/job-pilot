import json
import sqlite3

db = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
db.row_factory = sqlite3.Row
print('attempts', [dict(r) for r in db.execute('select outcome, count(*) n from attempts group by outcome')])
print('blocked', db.execute("select count(*) from jobs where status='blocked'").fetchone()[0])
for r in db.execute("select id, data, reason from jobs where status='blocked'"):
    d = json.loads(r['data'])
    print(' ', r['id'], d.get('title'), '|', d.get('company'), '|', (r['reason'] or '')[:40])
print('dup external_id', [dict(r) for r in db.execute('select external_id, count(*) n from jobs group by external_id having n>1')])
print('companies with >1 sent', [dict(r) for r in db.execute("""
    select json_extract(j.data,'$.company') c, count(*) n from attempts a join jobs j on j.id=a.job_id
    where a.mode='live' and a.outcome='sent' group by c having n>1 order by n desc limit 8""")])
