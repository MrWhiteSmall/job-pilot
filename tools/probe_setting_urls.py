from pathlib import Path

from browser_adapter import browser

URLS = [
    'https://www.zhipin.com/web/geek/setting',
    'https://www.zhipin.com/web/geek/setting/',
    'https://www.zhipin.com/web/geek/chat?setting=1',
]

page = None
try:
    browser._context()
    page = browser.context.new_page()
    for url in URLS:
        try:
            browser._goto(page, url, timeout=25000)
            page.wait_for_timeout(2500)
            text = page.locator('body').inner_text(timeout=8000)
            print('URL', url, '->', page.url, '|', page.title())
            print('  has 招呼:', '招呼' in text, '| snippet:', ' '.join(text.split())[:160])
        except Exception as exc:
            print('URL', url, 'failed', type(exc).__name__, str(exc)[:120])
    shot = Path('data/screenshots/chat-setting.png')
    page.screenshot(path=str(shot))
    print('screenshot', shot)
finally:
    if page is not None:
        page.close()
    browser._close()
