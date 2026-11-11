import collections
import json
import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('data/job_pilot.sqlite3')
conn.row_factory = sqlite3.Row

print('=== 规则 ===')
row = conn.execute('SELECT data FROM rules WHERE id=1').fetchone()
rules = json.loads(row['data']) if row else {}
for key in ('cities', 'districts', 'titles', 'collect_titles', 'exclude_titles',
            'company_min', 'company_max', 'tiny_needs_funding', 'large_needs_foreign',
            'min_salary', 'max_salary', 'recruitment_type', 'max_education', 'accept_near_miss'):
    value = rules.get(key)
    if isinstance(value, list):
        print(f'{key:20} ({len(value)}) {value}')
    else:
        print(f'{key:20} {value}')
print('blacklist', len(rules.get('blacklist') or []), 'skills', len(rules.get('skills') or []))

print('\n=== 最近 12 次投递（本地时间 / 间隔秒） ===')
rows = conn.execute("SELECT created_at, outcome FROM attempts WHERE mode='live' ORDER BY id DESC LIMIT 12").fetchall()
prev = None
for r in rows:
    ts = datetime.fromisoformat(r['created_at'])
    gap = '' if prev is None else f"{(prev - ts).total_seconds():.0f}s"
    print(ts.astimezone().strftime('%H:%M:%S'), r['outcome'], gap)
    prev = ts

print('\n=== 今天的日志事件 ===')
for r in conn.execute("SELECT event, COUNT(*) n, MIN(created_at) first, MAX(created_at) last FROM logs WHERE created_at>='2026-11-09T16:00' GROUP BY event ORDER BY n DESC LIMIT 15"):
    print(f"{r['event']:16} {r['n']:5}  {r['first'][11:19]} -> {r['last'][11:19]}")

print('\n=== 拒绝原因（全库） ===')
reasons = collections.Counter()
for r in conn.execute("SELECT reason FROM jobs WHERE status='rejected' AND reason IS NOT NULL"):
    text = r['reason']
    key = text.split('：')[0].split('（')[0][:28]
    reasons[key] += 1
for key, n in reasons.most_common(12):
    print(f'{n:5}  {key}')
