import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import JobEngine

BASE = Path(__file__).resolve().parent.parent
o = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=1200):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    return json.loads(o.open(req, timeout=timeout).read().decode())


def fresh_stats():
    e = JobEngine(str(BASE / 'data' / 'job_pilot.sqlite3'))
    contacted = e.contacted_companies()
    with e._connect() as conn:
        rows = conn.execute("SELECT * FROM jobs WHERE status='matched'").fetchall()
    jobs = [dict(r) for r in rows]
    jobs = [j for j in jobs if e._company_key(json.loads(j['data']).get('company')) not in contacted]
    hi = [j for j in jobs if (j['score'] or 0) >= 55]
    return len(jobs), len(hi)


print('before fresh/>=55:', fresh_stats())
for i in range(3):
    try:
        r = call('/api/browser/enrich', {'limit': 10})
        print('enrich', i, 'checked', r.get('checked'), 'ok', r.get('ok'), 'failed', r.get('failed'))
    except Exception as exc:  # noqa: BLE001
        print('enrich failed', exc)
        break
for _ in range(30):
    st = call('/api/state')
    if not st['stats']['pending']:
        break
    call('/api/analyze', {})
    call('/api/run', {})
print('after fresh/>=55:', fresh_stats())
print('stats', json.dumps(call('/api/state')['stats'], ensure_ascii=False))
