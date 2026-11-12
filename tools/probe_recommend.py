"""Probe BOSS 推荐流：看 /web/geek/recommend 是否能拿到卡片，用现有 Chrome 会话。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import browser_adapter as ba  # noqa: E402

b = ba.BossBrowser()


def go():
    page = b._new_page()
    try:
        b._goto(page, 'https://www.zhipin.com/web/geek/jobs?city=101210100&query=AI', timeout=30000)
    except Exception as exc:  # noqa: BLE001
        print('goto failed', exc)
    page.wait_for_timeout(2500)
    print('url', page.url)
    for sel in ('.job-card-box', '.job-card-wrapper', '.job-list-box li', '.recommend-job-card'):
        try:
            print(sel, page.locator(sel).count())
        except Exception as exc:  # noqa: BLE001
            print(sel, 'err', str(exc)[:80])
    b._sweep()


out = b._call(go)
print(json.dumps({'ok': out}, ensure_ascii=False))
