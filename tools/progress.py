import collections
import json
import sqlite3
import urllib.request

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
state = json.loads(opener.open('http://127.0.0.1:8765/api/state', timeout=60).read().decode())
print('stats', json.dumps(state['stats'], ensure_ascii=False))
print('auto ', json.dumps(state['automation'], ensure_ascii=False))
print('jobs ', dict(collections.Counter(j['status'] for j in state['jobs'])))
for row in state['logs'][:8]:
    print(' log ', row['created_at'][11:19], row['event'], str(row['detail'])[:50])

db = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
print('today', list(db.execute(
    "select outcome, count(*) from attempts where date(created_at, '+8 hours')=date('now', '+8 hours') group by outcome")))
print('last sent:')
for created, data in db.execute(
        "select a.created_at, j.data from attempts a join jobs j on j.id=a.job_id "
        "where a.outcome='sent' order by a.id desc limit 6"):
    job = json.loads(data)
    print('  ', created[11:16], job.get('title'), '@', job.get('company'), job.get('city'), job.get('salary'))
