import json

from browser_adapter import browser

page = None
try:
    browser._context()
    page = browser.context.new_page()
    browser._goto(page, 'https://www.zhipin.com/web/geek/chat', timeout=30000)
    page.wait_for_timeout(3000)
    avatar = page.locator('.nav-figure, .user-nav, .header-login-btn, .nav-user').first
    print('avatar count', page.locator('.nav-figure, .user-nav, .nav-user').count())
    if avatar.count():
        avatar.hover()
        page.wait_for_timeout(1200)
        menu = page.evaluate("""
        () => {
          const out = [];
          document.querySelectorAll('div,ul,li,a,span').forEach(el => {
            const style = getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') return;
            const t = (el.innerText || '').trim();
            if (!t || t.length > 40 || t.includes('\\n')) return;
            if (!/设置|简历|账号|隐私|退出|帮助|我的/.test(t)) return;
            out.push({tag: el.tagName, cls: (el.className || '').toString().slice(0, 50), text: t});
          });
          return out.slice(-40);
        }
        """)
        print(json.dumps(menu, ensure_ascii=False, indent=1))
    page.screenshot(path='data/screenshots/avatar-menu.png')
    print('shot saved')
finally:
    if page is not None:
        page.close()
    browser._close()
