import json

from browser_adapter import browser

page = None
try:
    browser._context()
    page = browser.context.new_page()
    browser._goto(page, 'https://www.zhipin.com/web/geek/chat', timeout=30000)
    page.wait_for_timeout(3000)
    page.locator('.chat-user, .geek-chat-item, .user-list li, .chat-list li').first.click()
    page.wait_for_timeout(2000)
    info = page.evaluate("""
    () => {
      const out = {editors: [], buttons: [], search: []};
      document.querySelectorAll('[contenteditable="true"], textarea').forEach(el => {
        out.editors.push({tag: el.tagName, cls: (el.className || '').toString().slice(0, 70),
                          placeholder: el.getAttribute('placeholder') || el.getAttribute('data-placeholder') || ''});
      });
      document.querySelectorAll('button, a, div, span').forEach(el => {
        const t = (el.innerText || '').trim();
        if (t !== '发送') return;
        out.buttons.push({tag: el.tagName, cls: (el.className || '').toString().slice(0, 70)});
      });
      document.querySelectorAll('input').forEach(el => {
        out.search.push({cls: (el.className || '').toString().slice(0, 60),
                         placeholder: el.getAttribute('placeholder') || ''});
      });
      return out;
    }
    """)
    print(json.dumps(info, ensure_ascii=False, indent=1))
finally:
    if page is not None:
        page.close()
    browser._close()
