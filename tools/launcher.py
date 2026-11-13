"""一键安装 / 启动 / 停止 / 状态。只依赖标准库，任何 Python 3.8+ 都能跑。

用法：
    python tools/launcher.py setup     # 检查并安装依赖
    python tools/launcher.py start     # 后台启动服务
    python tools/launcher.py stop      # 先暂停托管，再停进程
    python tools/launcher.py status    # 看当前托管与投递状态
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAVED = ROOT / 'data' / 'python-path.txt'
PORT = os.getenv('JOB_PILOT_PORT', '8765')
BASE = f'http://127.0.0.1:{PORT}'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
IMPORTS = 'import flask, requests, pypdf, playwright'
MARKERS = ('app.py', 'watchdog.py', 'monitor.py', 'ensure_alive.py')


def say(text=''):
    print(text, flush=True)


def api(path, payload=None, timeout=30):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={'Content-Type': 'application/json'})
    return json.loads(OPENER.open(req, timeout=timeout).read().decode('utf-8'))


def online(timeout=10):
    try:
        api('/api/state', timeout=timeout)
        return True
    except Exception:
        return False


def candidates():
    """按优先级列出可能的解释器命令。"""
    seen, out = set(), []

    def add(cmd):
        key = tuple(cmd)
        if key not in seen:
            seen.add(key)
            out.append(list(cmd))

    if os.getenv('JOB_PILOT_PYTHON'):
        add([os.getenv('JOB_PILOT_PYTHON')])
    if SAVED.exists():
        value = SAVED.read_text('utf-8').strip()
        if value:
            add([value])
    add([sys.executable])
    for name in ('python', 'python3'):
        path = shutil.which(name)
        if path:
            add([path])
    add(['py', '-3'])
    for base in (r'D:\Anaconda3\python.exe',
                 Path(os.getenv('LOCALAPPDATA', '')) / 'Programs' / 'Python'):
        if isinstance(base, Path):
            for child in sorted(base.glob('Python3*/python.exe'), reverse=True):
                add([str(child)])
        elif Path(base).exists():
            add([base])
    return out


def probe(cmd, args):
    try:
        done = subprocess.run(cmd + args, capture_output=True, text=True, timeout=60)
        return done.returncode == 0, (done.stdout + done.stderr).strip()
    except Exception as exc:
        return False, str(exc)


def has_deps(cmd):
    return probe(cmd, ['-c', IMPORTS])[0]


def pick(with_deps=True, need_pip=False):
    for cmd in candidates():
        ok = probe(cmd, ['-c', 'import sys; print(sys.version.split()[0])'])[0]
        if not ok:
            continue
        if with_deps and not has_deps(cmd):
            continue
        if need_pip and not probe(cmd, ['-m', 'pip', '--version'])[0]:
            continue
        return cmd
    return None


def remember(cmd):
    SAVED.parent.mkdir(parents=True, exist_ok=True)
    SAVED.write_text(cmd[-1] if cmd[:1] == ['py'] else cmd[0], encoding='utf-8')


def setup():
    say('== Job Pilot 依赖安装 ==')
    targets = []
    for cmd in candidates():
        ok, version = probe(cmd, ['-c', 'import sys; print(sys.version.split()[0])'])
        if not ok:
            continue
        deps = has_deps(cmd)
        pip = probe(cmd, ['-m', 'pip', '--version'])[0]
        say(f'  {" ".join(cmd)}  ->  Python {version}  依赖{"已装" if deps else "缺失"}  pip{"可用" if pip else "不可用"}')
        if pip:
            targets.append(cmd)
        if deps and pip:
            remember(cmd)
            say('')
            say(f'√ 这个解释器已经装好依赖，直接可用：{" ".join(cmd)}')
            say('  下一步：双击「一键启动.cmd」')
            return 0
    if not targets:
        say('')
        say('× 没找到可用的 Python + pip。请先安装 Python 3.10+（勾选 Add to PATH），再重跑本脚本。')
        return 1

    cmd = targets[0]
    say('')
    say(f'→ 使用 {" ".join(cmd)} 安装依赖（Flask / requests / pypdf / playwright）')
    code = subprocess.call(cmd + ['-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')])
    if code != 0:
        say('× 安装失败。常见原因：网络需要代理、pip 版本过旧（可先 python -m pip install -U pip）。')
        return code
    if not has_deps(cmd):
        say('× 安装完成但仍无法 import，可能有多个 Python 混用。请用同一解释器重试。')
        return 1
    remember(cmd)
    say('')
    say('√ 依赖安装完成')
    say('  浏览器要求：本机安装 Google Chrome（不需要另外下载 Playwright 的 Chromium）')
    say('  下一步：双击「一键启动.cmd」')
    return 0


def start():
    if online():
        say(f'√ 服务已在运行：{BASE}')
        say('  要重启请先运行「一键停止.cmd」')
        return 0
    cmd = pick(with_deps=True)
    if not cmd:
        say('× 没有找到已安装依赖的 Python。请先双击「一键安装依赖.cmd」。')
        return 1
    data = ROOT / 'data'
    data.mkdir(parents=True, exist_ok=True)
    log = (data / 'app.out.log').open('ab')
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    subprocess.Popen(cmd + ['app.py'], cwd=str(ROOT), stdin=subprocess.DEVNULL,
                     stdout=log, stderr=log, creationflags=flags, close_fds=True)
    say(f'→ 启动中（{" ".join(cmd)} app.py）')
    for _ in range(30):
        time.sleep(1)
        if online(timeout=3):
            say(f'√ 已启动：{BASE}')
            say('  首次使用：页面上「连接 BOSS」扫码登录，填简历，先跑模拟再切真实。')
            say(f'  日志：{data / "app.out.log"}')
            return 0
    say('× 30 秒内没起来。看日志最后几行：')
    tail = (data / 'app.out.log').read_text('utf-8', errors='replace').splitlines()[-12:]
    for line in tail:
        say('  ' + line)
    return 1


def find_pids():
    script = ("Get-CimInstance Win32_Process -Filter \"Name = 'python.exe' or Name = 'pythonw.exe'\" | "
              "Where-Object { $_.CommandLine -like '*job-pilot*' -or $_.CommandLine -like '*app.py*' } | "
              "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress")
    try:
        out = subprocess.run(['powershell', '-NoProfile', '-Command', script],
                             capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception:
        return []
    if not out:
        return []
    rows = json.loads(out)
    if isinstance(rows, dict):
        rows = [rows]
    keep = []
    for row in rows:
        line = str(row.get('CommandLine') or '')
        if not any(marker in line for marker in MARKERS):
            continue
        if 'job-pilot' not in line.lower() and str(ROOT).lower() not in line.lower():
            # 别的目录的 app.py 不动
            if 'app.py' not in line:
                continue
        keep.append(int(row['ProcessId']))
    return keep


def stop():
    say('== 停止 Job Pilot ==')
    if online():
        try:
            cfg = api('/api/state')['automation']
            cfg['enabled'] = False
            api('/api/automation', cfg)
            say('√ 已先暂停托管（正在发出的那一条会走完）')
        except Exception as exc:
            say(f'· 暂停托管失败（继续停进程）：{exc}')
    pids = find_pids()
    if pids:
        for pid in pids:
            subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True, text=True)
        say(f'√ 已结束进程：{", ".join(map(str, pids))}')
    else:
        say('· 没有找到运行中的进程')
    time.sleep(2)
    say('√ 已停止' if not online() else '× 端口仍在响应，请手动检查后台进程')
    return 0


def status():
    if not online():
        say('× 服务未运行。双击「一键启动.cmd」')
        return 1
    state = api('/api/state')
    cfg, stats = state['automation'], state['stats']
    say(f'服务：{BASE}')
    say(f'托管：{"运行中" if cfg["enabled"] else "已暂停"}  模式：{"真实 BOSS" if cfg["mode"] == "live" else "模拟"}  '
        f'日上限：{cfg["daily_limit"]}  间隔：{cfg["interval_seconds"]}s  分数门槛：{cfg["min_score"]:g}')
    say(f'已沟通：{stats["sent"]}  今日剩余：{stats["today_remaining"]}  队列：{stats["shortlisted"]}  '
        f'库存：{stats["jobs"]}  待分析：{stats["pending"]}')
    try:
        busy = api('/api/browser/busy')
        say(f'浏览器：{busy["name"] or "空闲"} {int(busy["seconds"])}s')
    except Exception:
        pass
    for row in (state.get('alerts') or [])[:2]:
        say(f'告警：{row.get("detail") or row.get("event")}')
    return 0


def main(argv):
    action = (argv[1] if len(argv) > 1 else 'status').lower()
    table = {'setup': setup, 'install': setup, 'start': start, 'stop': stop, 'status': status}
    if action not in table:
        say('用法：python tools/launcher.py [setup|start|stop|status]')
        return 2
    return table[action]()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
