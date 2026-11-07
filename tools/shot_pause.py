from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:8765', wait_until='networkidle')
    page.wait_for_selector('#pauseBtn', timeout=10000)
    label = page.inner_text('#pauseBtn')
    box = page.locator('#pauseBtn').bounding_box()
    visible = page.locator('#pauseBtn').is_visible()
    print('label', label, 'visible', visible, 'box', box)
    page.locator('#pauseBtn').scroll_into_view_if_needed()
    page.screenshot(path='data/screenshots/pause-button.png')
    print('errors', errors)
    browser.close()
