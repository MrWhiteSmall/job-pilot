"""Probe one BOSS job page for a machine-readable salary (attributes, fonts, inline JSON)."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3

from browser_adapter import BossBrowser

db = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
row = db.execute("SELECT data FROM jobs WHERE status='sent' ORDER BY id DESC LIMIT 1").fetchone()
url = json.loads(row[0]).get('url')

b = BossBrowser()
try:
    page = b._new_page()
    b._goto(page, url, timeout=25000)
    info = page.evaluate("""() => {
      const out = {fonts: [], nodes: [], json: []};
      for (const f of document.fonts) out.fonts.push({family: f.family, weight: f.weight, status: f.status});
      const sel = ['.job-banner .salary', '.job-primary .salary', '.job-info .salary', '.salary', '[class*=salary]'];
      for (const s of sel) for (const el of document.querySelectorAll(s)) {
        out.nodes.push({sel: s, text: el.textContent.trim().slice(0, 40),
          html: el.outerHTML.slice(0, 300),
          attrs: Array.from(el.attributes).map(a => [a.name, a.value.slice(0, 80)])});
      }
      const body = document.body.innerHTML;
      for (const m of body.matchAll(/"(salary|salaryMin|salaryMax|salaryMonth)"\\s*:\\s*"?([^",}]{0,30})/g)) out.json.push(m.slice(0, 3));
      return out;
    }""")
    print(json.dumps(info, ensure_ascii=False)[:3000])
    print('style fonts:', page.evaluate("""() => Array.from(document.styleSheets).flatMap(s => {try {return Array.from(s.cssRules).filter(r => r.cssText && r.cssText.includes('@font-face')).map(r => r.cssText.slice(0, 200));} catch (e) {return [];}})"""))
finally:
    b.close()
