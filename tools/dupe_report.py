import json
import re
import sqlite3
from collections import Counter, defaultdict

DB = r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3'
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row

rows = c.execute("SELECT id, external_id, data, status, created_at FROM jobs").fetchall()
print('jobs total:', len(rows))
urls = Counter()
titles = defaultdict(list)
companies = Counter()
for r in rows:
    d = json.loads(r['data'])
    url = (d.get('url') or r['external_id'] or '').strip()
    urls[url] += 1
    company = re.sub(r'\s+', '', d.get('company') or '')
    title = re.sub(r'[\s\u3000（）()\[\]【】·\-—_/]+', '', d.get('title') or '')
    titles[(company, title)].append(r['id'])
    companies[company] += 1

print('distinct url:', len(urls), '| url 重复:', sum(1 for v in urls.values() if v > 1))
dup_title = {k: v for k, v in titles.items() if len(v) > 1}
print('同公司+同标题（归一化后）重复组:', len(dup_title), '| 涉及岗位:', sum(len(v) for v in dup_title.values()))
for (company, title), ids in list(sorted(dup_title.items(), key=lambda kv: -len(kv[1])))[:8]:
    print('   ', company[:16], '|', title[:26], '|', len(ids), '条 ids=', ids[:6])

print('同公司多岗位（>1 条）:', sum(1 for v in companies.values() if v > 1), '家')

print('--- import 日志（最近 12 条）')
for r in c.execute("SELECT created_at, detail FROM logs WHERE event='import' ORDER BY id DESC LIMIT 12"):
    print(' ', r['created_at'][11:19], r['detail'])

print('--- 按小时新增岗位（最近 10 小时）')
for r in c.execute(
    "SELECT substr(created_at,1,13) AS h, COUNT(*) AS n FROM jobs GROUP BY h ORDER BY h DESC LIMIT 10"
):
    print(' ', r['h'], r['n'])

print('--- 每个公司的 live 沟通次数 >1')
for r in c.execute(
    "SELECT j.data, COUNT(*) AS n FROM attempts a JOIN jobs j ON j.id=a.job_id "
    "WHERE a.mode='live' AND a.outcome IN ('sent','uncertain','blocked') "
    "GROUP BY substr(j.data,1,0)||j.id HAVING n>1"
):
    pass
comp = Counter()
for r in c.execute(
    "SELECT j.data FROM attempts a JOIN jobs j ON j.id=a.job_id "
    "WHERE a.mode='live' AND a.outcome IN ('sent','uncertain','blocked')"
):
    comp[re.sub(r'\s+', '', json.loads(r['data']).get('company') or '')] += 1
bad = {k: v for k, v in comp.items() if v > 1}
print('同一公司被沟通多次:', len(bad), bad)
