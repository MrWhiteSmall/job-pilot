import json
import re
import subprocess
import urllib.request

PROFILE = 'D:\\DesktopCode\\job-pilot\\data\\boss-chrome-profile'
ps = (
    "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
    "Select-Object -ExpandProperty CommandLine"
)
out = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True).stdout
ports = set()
for line in out.splitlines():
    if PROFILE.lower() in line.lower() and '--type=' not in line:
        m = re.search(r'--remote-debugging-port=(\d+)', line)
        if m:
            ports.add(m.group(1))
print('ports', sorted(ports))
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for port in sorted(ports):
    try:
        data = json.load(opener.open('http://127.0.0.1:%s/json/list' % port, timeout=3))
    except Exception as exc:
        print(port, 'ERR', type(exc).__name__, str(exc)[:80])
        continue
    pages = [d for d in data if d.get('type') == 'page']
    print(port, 'pages', len(pages))
    for p in pages[:10]:
        print('  ', (p.get('title') or '')[:30], '|', (p.get('url') or '')[:90])
