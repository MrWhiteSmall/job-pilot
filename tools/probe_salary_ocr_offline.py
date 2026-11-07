"""Validate local OCR on a cropped salary from an existing screenshot."""
import json
import sys
import threading
from pathlib import Path

from PIL import Image
from winocr import recognize_pil_sync


def ocr(image, lang='zh-Hans-CN'):
    box = {}

    def run():
        try:
            box['value'] = ' '.join(line.text for line in recognize_pil_sync(image, lang).lines).strip()
        except Exception as exc:
            box['value'] = f'ERR {exc}'

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(30)
    return box.get('value', 'ERR timeout')


source = Image.open(r'D:\DesktopCode\job-pilot\data\screenshots\chrome-live.png').convert('RGB')
crops = {
    'card1': (795, 790, 910, 815),
    'card2': (1090, 1120, 1190, 1145),
}
for name, rect in crops.items():
    image = source.crop(rect)
    image = image.resize((image.width * 4, image.height * 4), Image.LANCZOS)
    print(json.dumps({'crop': name, 'ocr': ocr(image)}, ensure_ascii=False))
