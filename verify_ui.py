"""Local UI smoke check; never invokes BOSS endpoints or changes user data."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
output = ROOT / 'data' / 'screenshots'
output.mkdir(parents=True, exist_ok=True)
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    response = page.goto('http://127.0.0.1:8765', wait_until='networkidle')
    assert response.status == 200, 'Homepage failed'
    assert page.locator('h1').inner_text(), 'Missing app heading'
    assert page.locator('#jobCount').count() == 1, 'Job list missing'
    assert page.locator('#connection').inner_text() != '等待连接', 'App failed to initialize'
    assert page.locator('#resumeText').input_value(), 'Resume not loaded'
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Desktop horizontal overflow'
    page.screenshot(path=str(output / 'desktop.png'))
    page.locator('[data-view="rules"]').first.click()
    rules = page.evaluate("fetch('/api/state').then(r => r.json()).then(s => s.rules.data || s.rules)")
    for selector, key in [('#ruleCompanyMin', 'company_min'), ('#ruleCompanyMax', 'company_max'), ('#ruleRecruitment', 'recruitment_type'), ('#ruleEducation', 'max_education')]:
        assert page.locator(selector).input_value() == str(rules.get(key, '')), f'Rule UI mismatch: {key}'
    page.screenshot(path=str(output / 'rules.png'))
    page.locator('[data-view="resume"]').first.click()
    page.locator('[data-view="logs"]').first.click()
    page.locator('[data-view="desk"]').first.click()
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_function("document.querySelector('#sidebar').getBoundingClientRect().right <= 1")
    assert page.locator('.main').bounding_box()['width'] >= 380, 'Mobile content squeezed by sidebar'
    page.evaluate('window.scrollTo(0, 0)')
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile horizontal overflow'
    page.screenshot(path=str(output / 'mobile.png'))
    browser.close()
assert not errors, json.dumps(errors, ensure_ascii=False)
print('UI smoke passed: state, resume, navigation, desktop/mobile layout, no JavaScript exceptions.')
