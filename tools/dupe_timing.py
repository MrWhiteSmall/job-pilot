import json
import re
import sqlite3

DB = r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3'
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row

print('--- 公司级重复沟通的时间戳（看是否发生在去重上线 2026-11-06T08:55Z 之后）')
rows = c.execute(
    "SELECT a.id, a.job_id, a.outcome, a.created_at, j.data FROM attempts a "
    "JOIN jobs j ON j.id=a.job_id WHERE a.mode='live' "
    "AND a.outcome IN ('sent','uncertain','blocked') ORDER BY a.created_at"
).fetchall()
per_company = {}
for r in rows:
    d = json.loads(r['data'])
    key = re.sub(r'\s+', '', d.get('company') or '')
    per_company.setdefault(key, []).append((r['created_at'], r['job_id'], (d.get('title') or '')[:18]))
for comp, items in per_company.items():
    if len(items) > 1:
        print(comp[:18], [(t[0][5:16], t[1], t[2]) for t in items])

print('--- 近 24 小时采集进库的岗位里，同公司+同标题的重复')
recent = c.execute(
    "SELECT id, data, created_at FROM jobs WHERE created_at >= '2026-11-08T00' ORDER BY id"
).fetchall()
groups = {}
for r in recent:
    d = json.loads(r['data'])
    comp = re.sub(r'\s+', '', d.get('company') or '')
    title = re.sub(r'[\s\u3000（）()\[\]【】·\-—_/]+', '', d.get('title') or '')
    groups.setdefault((comp, title), []).append((r['id'], r['created_at'][5:16]))
dup = {k: v for k, v in groups.items() if len(v) > 1}
print('近 24h 新增', len(recent), '条，其中同公司同标题重复', len(dup), '组')
for (comp, title), ids in list(dup.items())[:10]:
    print('   ', comp[:16], '|', title[:24], '|', ids)
