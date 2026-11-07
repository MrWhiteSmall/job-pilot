import sqlite3

c = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
for t in ('automation', 'rules', 'profile', 'jobs'):
    try:
        print(t, [r[1] for r in c.execute('PRAGMA table_info(%s)' % t)])
    except Exception as exc:
        print(t, exc)
print([r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")])
