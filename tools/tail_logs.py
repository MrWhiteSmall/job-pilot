import sqlite3
import sys

conn = sqlite3.connect('data/job_pilot.sqlite3')
conn.row_factory = sqlite3.Row
since = sys.argv[1] if len(sys.argv) > 1 else '2026-11-11T00:00'
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 30
rows = conn.execute(
    "SELECT created_at, event, COALESCE(detail,'') d FROM logs WHERE created_at>=? ORDER BY id DESC LIMIT ?",
    (since, limit),
).fetchall()
for r in rows:
    print(r['created_at'][11:19], f"{r['event']:14}", r['d'][:110])
