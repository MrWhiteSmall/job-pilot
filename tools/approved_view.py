import sqlite3

conn = sqlite3.connect('data/job_pilot.sqlite3')
conn.row_factory = sqlite3.Row
print('status:', [(r['status'], r['n']) for r in conn.execute("SELECT status, COUNT(*) n FROM jobs GROUP BY status ORDER BY n DESC")])
print('approved jobs:')
for r in conn.execute("SELECT j.id, j.score, j.status, d.approved, substr(j.data,1,0) FROM jobs j LEFT JOIN drafts d ON d.job_id=j.id WHERE j.status='approved' ORDER BY j.id DESC LIMIT 10"):
    print(' ', r['id'], r['score'], r['status'], 'draft_approved=', r['approved'])
print('queued live attempts:', conn.execute("SELECT COUNT(*) FROM attempts WHERE mode='live'").fetchone()[0])
