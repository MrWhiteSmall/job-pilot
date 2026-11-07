"""Screenshot each card's salary element and OCR it locally (Windows OCR, own thread)."""
import io
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image
from winocr import recognize_pil_sync

from browser_adapter import BossBrowser  # noqa: E402


def ocr(image, lang='zh-Hans-CN'):
    """winocr runs asyncio.run internally, so keep it off Playwright's loop thread."""
    box = {}

    def run():
        try:
            box['value'] = ' '.join(line.text for line in recognize_pil_sync(image, lang).lines).strip()
        except Exception as exc:  # pragma: no cover - diagnostics only
            box['value'] = f'ERR {exc}'

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(30)
    return box.get('value', 'ERR timeout')


browser = BossBrowser()
try:
    page = browser._new_page()
    browser._goto(page, 'https://www.zhipin.com/web/geek/jobs?city=101210100&query=AI', timeout=45000)
    page.wait_for_selector('.job-card-wrapper, .job-card-box', timeout=20000)
    page.wait_for_timeout(2000)
    cards = page.locator('.job-card-wrapper, .job-card-box')
    total = min(cards.count(), 6)
    for i in range(total):
        card = cards.nth(i)
        salary = card.locator('.salary, .job-salary').first
        if not salary.count():
            continue
        title = card.locator('.job-name').first.inner_text()[:14]
        box = salary.bounding_box()
        if not box:
            continue
        image = Image.open(io.BytesIO(page.screenshot(clip=box, animations='disabled', timeout=15000))).convert('RGB')
        image = image.resize((image.width * 3, image.height * 3), Image.LANCZOS)
        print(json.dumps({'title': title, 'raw': salary.inner_text().strip(), 'ocr': ocr(image)}, ensure_ascii=False))
finally:
    browser.close()


