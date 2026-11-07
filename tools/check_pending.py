"""Exit 1 when a live attempt is still marked pending (i.e. a send is in flight).

Run this before restarting app.py: killing the process mid-send leaves the job in
an unknown state (recorded as `uncertain` on the next start).

    python tools/check_pending.py
    if ($LASTEXITCODE -eq 0) { ... safe to restart ... }
"""

import os
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB = Path(os.getenv('JOB_PILOT_DB', str(BASE / 'data' / 'job_pilot.sqlite3')))

if not DB.is_file():
    print('no database yet:', DB)
    sys.exit(0)

db = sqlite3.connect(str(DB))
pending = db.execute("SELECT COUNT(*) FROM attempts WHERE outcome='pending'").fetchone()[0]
print('pending_attempts', pending)
sys.exit(1 if pending else 0)
