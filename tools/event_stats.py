import collections
import sqlite3
from pathlib import Path

conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent / 'data' / 'job_pilot.sqlite3'))
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT event, COUNT(*) n, MAX(created_at) last FROM logs WHERE created_at>='2026-11-10T02:00' GROUP BY event ORDER BY last DESC").fetchall()
for r in rows:
    print(f"{r['event']:16} {r['n']:4}  {r['last']}")
print('--- last 12 logs ---')
for r in conn.execute("SELECT created_at, event, substr(COALESCE(detail,''),1,70) d FROM logs ORDER BY id DESC LIMIT 12"):
    print(r['created_at'][11:19], f"{r['event']:14}", r['d'])
