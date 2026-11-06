"""Keep the local job-pilot app alive without a human watching it.

- Restarts app.py when the dashboard stops answering.
- Re-enables automation only after transient failures (worker error / crawl failure),
  never after a deliberate platform stop (quota, login, captcha).
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / 'data' / 'watchdog.json'
LOG = ROOT / 'data' / 'watchdog.log'
BASE = 'http://127.0.0.1:8765'
DEFAULTS = {
    'enabled': True, 'mode': 'live', 'daily_limit': 150,
    'interval_seconds': 70, 'min_score': 40,
    'auto_approve': True, 'auto_collect': True,
}
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
LAST_ENRICH = 0.0


def note(message):
    stamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with LOG.open('a', encoding='utf-8') as handle:
        handle.write(f'{stamp} {message}\n')


def call(path, body=None, timeout=20):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method='POST' if data else 'GET',
                                     headers={'Content-Type': 'application/json'})
    with OPENER.open(request, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def config():
    if CONFIG.exists():
        try:
            saved = json.loads(CONFIG.read_text(encoding='utf-8'))
            return {**DEFAULTS, **saved}
        except Exception:
            pass
    return dict(DEFAULTS)


def kill_app():
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*app.py*' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    subprocess.run(['powershell', '-NoProfile', '-Command', script], capture_output=True)


def start_app():
    subprocess.Popen(
        ['cmd.exe', '/c', 'python app.py > data\\app.out.log 2>&1'],
        cwd=str(ROOT), creationflags=0x00000008,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def resume():
    settings = config()
    settings['enabled'] = True
    call('/api/automation', settings)


def keep_queue_full(state):
    """Top up the approved queue by reading full postings for the best matches."""
    global LAST_ENRICH
    stats = state.get('stats') or {}
    if (stats.get('shortlisted') or 0) >= 8 or (stats.get('today_remaining') or 0) <= 0:
        return
    if time.monotonic() - LAST_ENRICH < 240:
        return
    LAST_ENRICH = time.monotonic()
    try:
        done = call('/api/browser/enrich', {'limit': 10}, timeout=600)
        note(f"补充岗位详情：成功 {done.get('ok')} 条，失败 {done.get('failed')} 条")
    except Exception as exc:
        note(f'补充岗位详情失败：{exc}')


def tick():
    try:
        state = call('/api/state')
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        note(f'接口不可用，准备重启：{exc}')
        kill_app()
        time.sleep(2)
        start_app()
        time.sleep(8)
        for _ in range(6):
            try:
                call('/api/state')
                break
            except Exception:
                time.sleep(5)
        try:
            resume()
            note('已重启并恢复托管')
        except Exception as exc:
            note(f'重启后仍无法恢复：{exc}')
        return

    automation = state.get('automation') or {}
    if automation.get('enabled'):
        keep_queue_full(state)
        return
    pending = any(a.get('outcome') == 'pending' for a in (state.get('attempts') or []))
    if pending:
        note('托管暂停但仍有进行中的记录，等待人工核对')
        return
    logs = state.get('logs') or []
    last = (logs[0].get('event') or logs[0].get('kind')) if logs else None
    if last in ('worker_error', 'collect_blocked'):
        try:
            resume()
            note(f'上次为 {last}，已自动恢复托管')
        except Exception as exc:
            note(f'自动恢复失败：{exc}')
    else:
        note(f'托管处于暂停状态（最近事件 {last}），保留人工确认')


if __name__ == '__main__':
    LOG.parent.mkdir(parents=True, exist_ok=True)
    note('看门狗启动')
    while True:
        try:
            tick()
        except Exception as exc:
            note(f'看门狗异常：{exc}')
        time.sleep(45)
