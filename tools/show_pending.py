import sqlite3

db = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
print('pending rows:')
for row in db.execute("SELECT id, job_id, mode, outcome, created_at FROM attempts WHERE outcome='pending'"):
    print(' ', row)
print('recent logs:')
for row in db.execute('SELECT id, event, substr(detail, 1, 60), created_at FROM logs ORDER BY id DESC LIMIT 5'):
    print(' ', row)
print('now(utc):', db.execute("SELECT datetime('now')").fetchone()[0])
