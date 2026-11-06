"""Read-only live browser inspection; never clicks contact buttons."""
import json
from pathlib import Path
from browser_adapter import browser


def inspect():
    context = browser._context()
    page = context.new_page()
    try:
        page.goto('https://www.zhipin.com/web/geek/jobs?city=101210100&query=AI%E5%BA%94%E7%94%A8', wait_until='domcontentloaded')
        try:
            page.wait_for_function("() => document.body && document.body.innerText.trim().length > 100", timeout=25000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
        output = {'url': page.url, 'title': page.title(), 'body': page.locator('body').inner_text()[:6500]}
        output['cards'] = page.evaluate('''() => Array.from(document.querySelectorAll('[class]')).filter(e => /job.*(card|list)|card.*job/.test(e.className)).slice(0,30).map(e => ({tag:e.tagName,cls:e.className,text:e.innerText.slice(0,180),html:e.outerHTML.slice(0,1800)}))''')
        page.screenshot(path=str(Path('data/screenshots/boss-probe.png')), full_page=False)
        print(json.dumps(output, ensure_ascii=True))
    finally:
        page.close()

import socket
import subprocess
import time
import urllib.request
from playwright.sync_api import sync_playwright

profile = Path('data/boss-profile').resolve()
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
subprocess.Popen([r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                  '--user-data-dir=' + str(profile), '--remote-debugging-port=' + str(port),
                  '--remote-debugging-address=127.0.0.1', '--new-window', 'about:blank'])
with sync_playwright() as pw:
    for attempt in range(40):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1).close()
            break
        except Exception:
            time.sleep(0.25)
    browser_connection = pw.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
    browser._context = lambda: browser_connection.contexts[0]
    try:
        jobs = browser._collect({'titles': ['AI应用'], 'cities': ['杭州']})
        Path('data/boss-collected.json').write_text(json.dumps(jobs, ensure_ascii=False), encoding='utf-8')
        print(json.dumps({'count': len(jobs), 'examples': jobs[:2]}, ensure_ascii=True))
    finally:
        browser_connection.new_browser_cdp_session().send('Browser.close')
        browser_connection.close()
