import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
conn = sqlite3.connect(str(BASE / 'data' / 'job_pilot.sqlite3'))
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, outcome, created_at FROM attempts WHERE mode='live' ORDER BY id DESC LIMIT 25").fetchall()
prev = None
gaps = []
for row in rows:
    ts = datetime.fromisoformat(row['created_at'])
    if prev:
        gaps.append((ts - prev).total_seconds())
    prev = ts
print('attempts', len(rows))
print('gaps(sec)', [round(g) for g in gaps[:20]])
if gaps:
    print('avg', round(sum(gaps) / len(gaps)), 'median', sorted(gaps)[len(gaps) // 2])
today = [r for r in rows if str(r['created_at'])[:10] == datetime.utcnow().strftime('%Y-%m-%d')]
print('last 25 attempts span (min)', round((datetime.fromisoformat(rows[0]['created_at']) - datetime.fromisoformat(rows[-1]['created_at'])).total_seconds() / 60, 1))
