import json
import urllib.request

from playwright.sync_api import sync_playwright

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def enabled():
    data = json.loads(OPENER.open('http://127.0.0.1:8765/api/state', timeout=60).read().decode())
    return data['automation']['enabled']


print('start', enabled())
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    page.goto('http://127.0.0.1:8765', wait_until='networkidle')
    page.wait_for_selector('#pauseBtn')
    print('label', page.inner_text('#pauseBtn'))
    page.locator('#pauseBtn').click()
    page.wait_for_timeout(2500)
    print('after click ->', page.inner_text('#pauseBtn'), '| server', enabled())
    print('toast', page.inner_text('#toast'))
    page.locator('#pauseBtn').scroll_into_view_if_needed()
    page.screenshot(path='data/screenshots/pause-resume.png')
    page.locator('#pauseBtn').click()
    page.wait_for_timeout(2500)
    print('after second click ->', page.inner_text('#pauseBtn'), '| server', enabled())
    print('toast', page.inner_text('#toast'))
    browser.close()
