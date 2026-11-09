"""Apply the 0-20浜洪渶铻嶈祫 / 1000+浜洪渶澶栬祫 rule change, then rescore everything."""

import json
import urllib.request

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=1800):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    return json.loads(OPENER.open(req, timeout=timeout).read().decode())


rules = call('/api/state')['rules']
payload = {
    'company_min': 0,
    'company_max': 9999,
    'tiny_needs_funding': True,
    'large_needs_foreign': True,
    'blacklist': rules.get('blacklist') or [],
    'titles': rules.get('titles') or [],
    'collect_titles': rules.get('collect_titles') or [],
    'exclude_titles': rules.get('exclude_titles') or [],
    'skills': rules.get('skills') or [],
    'cities': rules.get('cities') or [],
    'districts': rules.get('districts') or [],
    'min_salary': rules.get('min_salary'),
    'max_salary': rules.get('max_salary'),
    'recruitment_type': rules.get('recruitment_type'),
    'max_education': rules.get('max_education'),
    'greeting': rules.get('greeting') or '',
}
print(json.dumps(call('/api/rules', payload), ensure_ascii=False)[:300])

