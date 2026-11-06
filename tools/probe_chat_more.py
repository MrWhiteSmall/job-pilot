import json

from browser_adapter import browser

page = None
try:
    browser._context()
    page = browser.context.new_page()
    browser._goto(page, 'https://www.zhipin.com/web/geek/chat', timeout=30000)
    page.wait_for_timeout(3000)
    more = page.locator('.label-list >> text=更多').first
    print('more count', page.locator('.label-list >> text=更多').count())
    if more.count():
        more.click()
        page.wait_for_timeout(1500)
    hits = page.evaluate("""
    () => {
      const out = [];
      document.querySelectorAll('li,a,span,button,div').forEach(el => {
        if (el.children.length > 1) return;
        const t = (el.innerText || '').trim();
        if (!t || t.length > 20) return;
        const box = el.getBoundingClientRect();
        if (box.width === 0 || box.height === 0) return;
        if (!/招呼|设置|自动|常用|快捷/.test(t)) return;
        out.push({tag: el.tagName, cls: (el.className || '').toString().slice(0, 60), text: t});
      });
      return out.slice(0, 30);
    }
    """)
    print(json.dumps(hits, ensure_ascii=False, indent=1))
    page.screenshot(path='data/screenshots/chat-more.png')
    print('shot saved')
finally:
    if page is not None:
        page.close()
    browser._close()
