import json
import sqlite3

db = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
db.row_factory = sqlite3.Row
for r in db.execute("select a.id, a.job_id, a.outcome, a.detail, a.created_at, j.data from attempts a join jobs j on j.id=a.job_id where a.outcome!='sent' order by a.id"):
    d = json.loads(r['data'])
    print(r['id'], r['job_id'], r['outcome'], '|', d.get('title'), '|', d.get('company'))
    print('   detail:', (r['detail'] or '')[:90])
print('--- same-company multiple sent detail ---')
for r in db.execute("""
    select a.id, a.created_at, json_extract(j.data,'$.company') c, json_extract(j.data,'$.title') t
    from attempts a join jobs j on j.id=a.job_id where a.mode='live' and a.outcome='sent'
    order by c, a.id"""):
    print(r['id'], r['created_at'][11:19], r['c'], '|', r['t'])
