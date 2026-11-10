import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import JobEngine

BASE = Path(__file__).resolve().parent.parent
e = JobEngine(str(BASE / 'data' / 'job_pilot.sqlite3'))
cfg = e.get_automation()
q = e.queue(cfg['min_score'], cfg['mode'])
print('queue', len(q), 'min_score', cfg['min_score'])
for j in q[:8]:
    d = j['data']
    print(j['id'], j['score'], (d.get('salary') or 'NO-SALARY')[:14], (d.get('company') or '')[:16], (d.get('title') or '')[:24])
