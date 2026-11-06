import json

from browser_adapter import browser

page = None
try:
    browser._context()
    page = browser.context.new_page()
    browser._goto(page, 'https://www.zhipin.com/web/geek/chat', timeout=30000)
    page.wait_for_timeout(3000)
    item = page.locator('.chat-user, .geek-chat-item, .user-list li, .chat-list li').first
    print('items', page.locator('.chat-user, .geek-chat-item, .user-list li, .chat-list li').count())
    if item.count():
        item.click()
        page.wait_for_timeout(2500)
    hits = page.evaluate("""
    () => {
      const out = [];
      document.querySelectorAll('*').forEach(el => {
        if (el.children.length > 2) return;
        const t = (el.innerText || '').trim();
        if (!t || t.length > 30) return;
        if (!/招呼|常用语|快捷|设置/.test(t)) return;
        out.push({tag: el.tagName, cls: (el.className || '').toString().slice(0, 60), text: t});
      });
      return out.slice(0, 30);
    }
    """)
    print(json.dumps(hits, ensure_ascii=False, indent=1))
    page.screenshot(path='data/screenshots/chat-open.png')
    print('shot saved')
finally:
    if page is not None:
        page.close()
    browser._close()
