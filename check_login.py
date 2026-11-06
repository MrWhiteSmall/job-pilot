"""Read the dedicated Chrome session without navigating or closing it."""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

port = sys.argv[1]
out = Path('data/screenshots')
out.mkdir(parents=True, exist_ok=True)
result = []
with sync_playwright() as pw:
    connection = pw.chromium.connect_over_cdp(f'http://127.0.0.1:{port}', timeout=15000)
    for context in connection.contexts:
        for page in context.pages:
            if 'zhipin.com' not in page.url:
                continue
            try:
                text = page.locator('body').inner_text(timeout=8000)
            except Exception as exc:
                text = f'<read failed: {exc}>'
            result.append({
                'url': page.url,
                'title': page.title(),
                'logged_in': ('消息' in text and '简历' in text),
                'login_prompt': ('扫码登录' in text or '手机扫码' in text or '登录/注册' in text),
                'job_cards': page.locator('.job-card-box,.job-card-wrapper').count(),
                'body_head': text[:160],
            })
            try:
                page.screenshot(path=str(out / 'chrome-status.png'), timeout=15000)
            except Exception as exc:
                result[-1]['screenshot_error'] = str(exc)[:120]
    # Deliberately do not call connection.close()/browser.close(): the window must stay open.
print(json.dumps(result, ensure_ascii=False))
