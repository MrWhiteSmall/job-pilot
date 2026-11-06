import json

from browser_adapter import browser

page = None
try:
    browser._context()
    page = browser.context.new_page()
    browser._goto(page, 'https://www.zhipin.com/web/geek/chat', timeout=30000)
    page.wait_for_timeout(3000)
    page.locator('.nav-figure, .user-nav, .nav-user').first.hover()
    page.wait_for_timeout(1000)
    href = page.evaluate("() => { const a = document.querySelector('a.personal-center'); return a ? a.href : ''; }")
    print('personal center href', href)
    if href:
        browser._goto(page, href, timeout=30000)
        page.wait_for_timeout(3500)
        text = page.locator('body').inner_text(timeout=8000)
        print('url', page.url, '| has 招呼:', '招呼' in text)
        print(' '.join(text.split())[:400])
        page.screenshot(path='data/screenshots/personal-center.png')
finally:
    if page is not None:
        page.close()
    browser._close()
