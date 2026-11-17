"""一分钟级保活：app 或看门狗挂了就拉起来。由 Windows 计划任务每 10 分钟调用一次。"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
NO_WINDOW = 0x08000000 if __import__('os').name == 'nt' else 0

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / 'data' / 'ensure.log'


def note(text):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open('a', encoding='utf-8') as fh:
        fh.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} {text}\n')


def alive():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        opener.open('http://127.0.0.1:8765/api/state', timeout=8).read()
        return True
    except Exception:
        return False


def pids_of(script_name):
    script = ("Get-CimInstance Win32_Process -Filter \"Name = 'pythonw.exe' or Name = 'python.exe'\" | "
              "Where-Object { $_.CommandLine -like '*%s*' } | "
              "Select-Object -ExpandProperty ProcessId") % script_name
    out = subprocess.run(['powershell', '-NoProfile', '-Command', script],
                         capture_output=True, text=True, timeout=30, creationflags=NO_WINDOW).stdout
    return [int(x) for x in out.split() if x.strip().isdigit()]


def spawn(module, window='Hidden'):
    python = Path(sys.executable).with_name('pythonw.exe')
    exe = python if python.exists() else Path(sys.executable)
    subprocess.Popen([str(exe), module], cwd=str(ROOT),
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL,
                     creationflags=0x00000008 | 0x00000200)


def port_open(host='127.0.0.1', port=8765, timeout=1.5):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def main():
    started = []
    if not alive() and not port_open():
        spawn('app.py')
        started.append('app')
        time.sleep(10)
    if not pids_of('watchdog.py'):
        spawn('tools/watchdog.py')
        started.append('watchdog')
    if started:
        note('已拉起：' + ', '.join(started))
        print('started', started)
    else:
        print('healthy')


if __name__ == '__main__':
    main()
