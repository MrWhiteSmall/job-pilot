import json
from pathlib import Path

from browser_adapter import browser

page = None
try:
    browser._context()
    page = browser.context.new_page()
    browser._goto(page, 'https://www.zhipin.com/web/geek/chat', timeout=30000)
    page.wait_for_timeout(4000)
    info = page.evaluate("""
    () => {
      const hits = [];
      document.querySelectorAll('a,button,span,div,li').forEach(el => {
        const t = (el.innerText || '').trim();
        if (!t || t.length > 12) return;
        if (!/招呼|设置|自动化|快捷/.test(t)) return;
        hits.push({tag: el.tagName, cls: el.className && el.className.toString().slice(0, 60), text: t,
                   href: el.getAttribute('href') || ''});
      });
      return hits.slice(0, 40);
    }
    """)
    print(json.dumps(info, ensure_ascii=False, indent=1))
    shot = Path('data/screenshots/chat-page.png')
    shot.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(shot))
    print('screenshot', shot)
finally:
    if page is not None:
        page.close()
    browser._close()
