"""Close extra tabs left open by earlier runs (attached to the live Chrome)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from browser_adapter import BossBrowser  # noqa: E402

if __name__ == '__main__':
    browser = BossBrowser()
    try:
        print(browser.tidy(keep=1))
    finally:
        browser.close()
