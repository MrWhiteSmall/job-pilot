"""定时体检：每 5 分钟记一次投递状态，卡住就写 WARN，方便事后看是哪一段慢。"""
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / 'data' / 'monitor.log'
OPEN = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def state():
    with OPEN.open('http://127.0.0.1:8765/api/state', timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    while True:
        stamp = datetime.now().strftime('%m-%d %H:%M:%S')
        try:
            s = state()
            st = s['stats']
            auto = s['automation']
            logs = s.get('logs') or []
            last_sent = next((l['created_at'] for l in logs if l['event'] == 'sent'), '')
            line = (f"{stamp} sent={st['sent']} attempts={st['attempts']} queue={st['shortlisted']} "
                    f"jobs={st['jobs']} left={st['today_remaining']} enabled={auto['enabled']} mode={auto['mode']}")
            warn = ''
            if auto['enabled'] and auto['mode'] == 'live' and st['today_remaining'] > 0:
                if last_sent:
                    age = (datetime.now(timezone.utc) - datetime.fromisoformat(last_sent)).total_seconds()
                    if age > 1200:
                        warn = f" WARN no-send {int(age // 60)}min"
            with LOG.open('a', encoding='utf-8') as fh:
                fh.write(line + warn + '\n')
        except Exception as exc:  # noqa: BLE001
            with LOG.open('a', encoding='utf-8') as fh:
                fh.write(f'{stamp} ERROR {type(exc).__name__}: {str(exc)[:120]}\n')
        time.sleep(300)


if __name__ == '__main__':
    main()
