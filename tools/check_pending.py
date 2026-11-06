import sqlite3
import sys

db = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
pending = db.execute("SELECT COUNT(*) FROM attempts WHERE outcome='pending'").fetchone()[0]
print('pending_attempts', pending)
sys.exit(1 if pending else 0)
