"""BOSS browser adapter. All Playwright operations stay on one owner thread.
The initial contact button uses BOSS's own greeting; it does not attach a PDF.
Unknown outcomes are returned as uncertain and must never be automatically retried.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse, urlencode
import atexit
import random
import re
import time

ROOT = Path(__file__).resolve().parent

MASK_SCRIPT = """
(() => {
  const noop = () => {};
  for (const key of ['log', 'table', 'clear', 'debug', 'info', 'warn', 'error', 'dir']) {
    try { console[key] = noop; } catch (e) {}
  }
  try { Object.defineProperty(navigator, 'webdriver', {get: () => undefined}); } catch (e) {}
  try {
    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
  } catch (e) {}
})();
"""


class BossBrowser:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='boss-browser')
        self.context = None
        self.playwright = None
        self.connection = None
        self.edge_endpoint = None
        self._opened = []
        atexit.register(self.close)

    def _call(self, fn, *args):
        # No Future timeout: timing out could leave an irreversible click running
        # while the caller starts another attempt. Playwright has bounded timeouts.
        return self.executor.submit(fn, *args).result()

    def _launch_edge(self, url='about:blank'):
        import socket
        import subprocess
        import urllib.request
        import os
        candidates = [Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
                      Path(r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'),
                      Path(os.environ.get('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe']
        browser_path = next((path for path in candidates if path.is_file()), None)
        if browser_path is None:
            raise RuntimeError('未找到本机 Chrome，请检查安装路径。')
        profile = ROOT / 'data' / 'boss-chrome-profile'
        profile.mkdir(parents=True, exist_ok=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        subprocess.Popen([str(browser_path), '--user-data-dir=' + str(profile),
                          '--remote-debugging-port=' + str(port),
                          '--remote-debugging-address=127.0.0.1',
                          '--disable-blink-features=AutomationControlled',
                          '--no-first-run', '--no-default-browser-check',
                          '--new-window', url],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True,
                         creationflags=0x00000008 | 0x00000200)  # DETACHED_PROCESS | NEW_PROCESS_GROUP
        endpoint = f'http://127.0.0.1:{port}'
        deadline = time.monotonic() + 12
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while time.monotonic() < deadline:
            try:
                with opener.open(endpoint + '/json/version', timeout=1):
                    self.edge_endpoint = endpoint
                    return
            except Exception:
                time.sleep(0.25)
        raise RuntimeError('未能连接专用 Chrome。若有旧版专用窗口占用资料目录，请关闭该窗口后重试。')

    def _discover_endpoint(self):
        """Reuse an already-open dedicated Chrome window instead of launching a second one.

        Two Chrome processes cannot share one --user-data-dir: the newcomer hands off to the
        running instance and exits, which previously left a dead debug port behind.
        """
        import subprocess
        import urllib.request
        profile = str((ROOT / 'data' / 'boss-chrome-profile').resolve())
        if not Path(profile).is_dir():
            return None
        script = (
            "$p = Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe'\" | "
            f"Where-Object {{ $_.CommandLine -like '*{profile}*' -and $_.CommandLine -notlike '*--type=*' }} | "
            "Select-Object -First 1; if ($p) { $p.CommandLine }"
        )
        try:
            proc = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
                                  capture_output=True, text=True, timeout=15,
                                  creationflags=0x08000000)
        except Exception:
            return None
        match = re.search(r'--remote-debugging-port=(\d+)', proc.stdout or '')
        if not match:
            return None
        endpoint = f'http://127.0.0.1:{match.group(1)}'
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(endpoint + '/json/version', timeout=2):
                return endpoint
        except Exception:
            return None

    def _endpoint_alive(self):
        if not self.edge_endpoint:
            return False
        import urllib.request
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(self.edge_endpoint + '/json/version', timeout=1) as response:
                return response.status == 200
        except Exception:
            return False

    def _detach(self):
        if self.playwright is not None:
            try:
                self.playwright.stop()
            except Exception:
                pass
        self.playwright = None
        self.connection = None
        self.context = None

    def _context(self):
        if self.context is not None and self.connection is not None and self.connection.is_connected():
            return self.context
        from playwright.sync_api import sync_playwright
        self._detach()
        if not self._endpoint_alive():
            # Reuse a window the user signed in to; only launch if none is running.
            self.edge_endpoint = self._discover_endpoint()
        if not self._endpoint_alive():
            self.edge_endpoint = None
            self._launch_edge()
        self.playwright = sync_playwright().start()
        try:
            self.connection = self.playwright.chromium.connect_over_cdp(self.edge_endpoint, timeout=30000)
            if not self.connection.contexts:
                raise RuntimeError('Chrome 已连接但尚未建立页面上下文，请点击「连接 BOSS」重开窗口。')
            self.context = self.connection.contexts[0]
            self._mask(self.context)
        except Exception:
            self._detach()
            self.edge_endpoint = None
            raise
        return self.context

    @staticmethod
    def _mask(context):
        """Neutralise the page-side checks BOSS uses to blank automation tabs.

        BOSS logs objects to console and inspects them when a CDP client serialises the
        arguments; once it notices, it replaces the tab with about:blank. Silencing the
        console API before page scripts run keeps the tab on the real page.
        """
        try:
            context.add_init_script(MASK_SCRIPT)
        except Exception:
            pass

    @staticmethod
    def _check(page):
        text = page.locator('body').inner_text(timeout=10000)
        if any(x in text for x in ['访问异常', '安全验证', '请完成验证', '滑动验证', '行为验证', '您的访问行为异常']):
            raise RuntimeError('BOSS 要求安全验证，请到浏览器手动完成，程序不会绕过验证。')
        return text

    def login(self):
        return self._call(self._login)

    def _login(self):
        # Reuse the window the user already signed in to, so the session is never lost.
        self._detach()
        existing = self._discover_endpoint()
        if existing:
            self.edge_endpoint = existing
            return {'status': 'opened', 'message': '已复用现有的求职 Chrome 窗口（保留当前登录）。若尚未登录，请在该窗口扫码，然后点击采集。'}
        self._launch_edge('https://www.zhipin.com/web/user/?ka=header-login')
        return {'status': 'opened', 'message': '已打开本机 Chrome 专用登录窗口。扫码成功后直接点击采集，无需手动关闭窗口，程序会复用同一会话。'}

    def status(self):
        return self._call(self._status)

    def _status(self):
        context = self._context()
        pages = []
        for page in context.pages:
            if 'zhipin.com' not in page.url:
                continue
            try:
                text = page.locator('body').inner_text(timeout=8000)
            except Exception as exc:
                pages.append({'url': page.url, 'error': str(exc)[:200]})
                continue
            card = page.locator('.job-card-box, .job-card-wrapper').first
            pages.append({
                'url': page.url,
                'title': page.title(),
                'logged_in': '消息' in text and '简历' in text,
                'login_prompt': any(x in text for x in ('扫码登录', '手机扫码', '登录/注册')),
                'job_cards': page.locator('.job-card-box, .job-card-wrapper').count(),
                'sample_card': card.evaluate('e => e.outerHTML.slice(0, 2500)') if card.count() else '',
            })
        return {'pages': pages}

    def collect(self, rules=None):
        return self._call(self._collect, rules or {})

    def _collect(self, rules):
        context = self._context()
        page = self._new_page()
        jobs = []
        try:
            titles = rules.get('collect_titles') or rules.get('titles') or rules.get('keywords') or ['AI应用开发工程师', '全栈工程师']
            if isinstance(titles, str):
                titles = [x.strip() for x in re.split('[,，\n]', titles) if x.strip()]
            # City is intentionally explicit. Other cities require extending the city-code map.
            cities = rules.get('cities') or ['杭州']
            if isinstance(cities, str):
                cities = [cities]
            if '杭州' not in cities:
                raise RuntimeError('当前 BOSS 采集器配置为杭州；其他城市请先导入岗位，或扩展城市编码。')
            # Server-side filters cut the noise (outsourcing shops, tiny teams, senior-only).
            # Codes follow BOSS's own filter vocabulary; an empty result falls back to unfiltered.
            filters = [('scale', '303,304'), ('experience', '104,105,106'),
                       ('degree', '204,205,206'), ('salary', '406')]
            plans = [filters, []]
            for active in plans:
                for query, page_no in [(q, n) for q in titles[:6] for n in (1, 3)]:
                    page.bring_to_front()
                    params = {'city': '101210100', 'query': query}
                    if active:
                        params.update(dict(active))
                    if page_no > 1:
                        params['page'] = page_no
                    self._goto(page, 'https://www.zhipin.com/web/geek/jobs?' + urlencode(params), timeout=25000)
                    self._check(page)
                    cards = page.locator('.job-card-wrapper, .job-card-box')
                    try:
                        page.wait_for_function("() => Array.from(document.querySelectorAll('.job-card-box a[href*=\"/job_detail/\"], .job-card-wrapper a[href*=\"/job_detail/\"]')).some(a => a.textContent.trim())", timeout=30000)
                    except Exception:
                        body = self._check(page)
                        if jobs:
                            break
                        debug_path = ROOT / 'data' / 'screenshots' / 'collect-blocked.png'
                        debug_path.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(debug_path))
                        if '登录' in body and not cards.count():
                            raise RuntimeError('尚未获得可读取的岗位列表，请先在独立浏览器登录 BOSS。') from None
                        continue
                    items = cards.evaluate_all("""cards => cards.slice(0, 15).map(c => {
                        const get = s => c.querySelector(s)?.textContent?.trim() || '';
                        const a = c.querySelector('a[href*="/job_detail/"]');
                        const tags = Array.from(c.querySelectorAll('.tag-list li')).map(e => e.textContent.trim());
                        const education = tags.find(t => /^(学历不限|博士|硕士|本科|大专|高中|中专|初中)/.test(t)) || (tags[1] === '不限' ? '不限' : '');
                        const experience = tags.find(t => /经验|年|在校|应届|实习/.test(t)) || '';
                        const hiringText = (get('.job-name') + ' ' + experience);
                        const recruitment = /实习/.test(hiringText) ? 'internship' : /应届|在校|校招|校园/.test(hiringText) ? 'campus' : /经验不限|年|社招/.test(hiringText) ? 'social' : '';
                        const size = c.innerText.match(/(?:\\d[\\d,]*\\s*[-–~至]\\s*\\d[\\d,]*|\\d[\\d,]*以上)\\s*人/);
                        return {education, experience, recruitment_type:recruitment, company_size:size?.[0] || '', title:get('.job-name') || a?.textContent?.trim() || '',
                            company:get('.company-name') || get('.boss-name'),
                            city:get('.job-area') || get('.job-area-wrapper') || get('.company-location'),
                            salary:get('.salary') || get('.job-salary'),url:a?.href || '',description:c.innerText,
                            source:'BOSS直聘'};
                    })""")
                    for item in items:
                        if not item['title'] or not item['url']:
                            continue
                        # Card text is factual but incomplete. The scorer must not infer missing JD.
                        item['description'] = '【列表摘要，完整要求请查看原岗位】\n' + item['description']
                        if re.search('[\ue000-\uf8ff]', item['salary']):
                            item['salary'] = ''
                            item['description'] += '\n【薪资使用自定义字体，需打开原岗位核验】'
                        jobs.append(item)
                if jobs:
                    break
            unique = list({j['url']: j for j in jobs}.values())
            # Read a bounded number of detail pages. The remaining cards explicitly
            # retain their summary label, rather than inventing missing requirements.
            detail = self._new_page()
            try:
                for item in unique[:8]:
                    try:
                        self._read_detail(detail, item)
                    except Exception:
                        # Stop detail expansion at a login/verification/selector barrier.
                        # Cards are still real and remain labeled as incomplete.
                        break
            finally:
                detail.close()
            return unique
        finally:
            page.close()
            self._sweep()

    def _sweep(self, keep=0):
        """Close tabs this automation opened, leaving the user's own tabs alone."""
        alive = []
        for page in getattr(self, '_opened', []):
            try:
                if page.is_closed():
                    continue
            except Exception:
                continue
            alive.append(page)
        self._opened = alive
        for page in alive[:max(0, len(alive) - keep)]:
            try:
                page.close()
            except Exception:
                pass
            self._opened.remove(page)

    def tidy(self, keep=1):
        return self._call(self._tidy, keep)

    def _tidy(self, keep=1):
        """Close every automation/search tab except the first `keep` ones."""
        context = self._context()
        closed = 0
        for page in list(context.pages)[max(1, keep):]:
            try:
                page.close()
                closed += 1
            except Exception:
                pass
        self._opened = []
        return {'closed': closed, 'remaining': len(context.pages)}

    def _new_page(self):
        page = self._context().new_page()
        self._opened.append(page)
        if len(self._opened) > 12:
            self._sweep(keep=2)
        return page

    def _goto(self, page, url, attempts=2, timeout=25000):
        """Navigate, retrying when Chrome leaves the tab on about:blank."""
        for index in range(attempts):
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            except Exception:
                if index == attempts - 1:
                    raise
            if page.url and not page.url.startswith('about:'):
                return page
            page.wait_for_timeout(1200)
        return page

    def _read_detail(self, page, item):
        """Fill factual fields from one job detail page. Missing values stay empty."""
        self._goto(page, item['url'], timeout=20000)
        self._check(page)
        jd = page.locator('.job-sec-text, .job-detail .text').first
        jd.wait_for(state='visible', timeout=6000)
        description = jd.inner_text().strip()
        if description:
            item['description'] = description[:15000]
        if not item.get('salary'):
            # The list card draws salary with a private-use font; the detail header
            # sometimes carries the same figure as plain text.
            for selector in ('.job-banner .salary', '.job-primary .salary', '.job-info .salary'):
                block = page.locator(selector).first
                if not block.count():
                    continue
                value = block.inner_text().strip()
                if value and not re.search('[\ue000-\uf8ff]', value):
                    item['salary'] = value
                    break
        if not item.get('company_size'):
            for text in page.locator('.sider-company, .job-company, .company-info').all_text_contents():
                flat = re.sub(r'\s+', ' ', text)
                size = re.search(r'(?:\d[\d,]*\s*[-–~至]\s*\d[\d,]*|\d[\d,]*以上)\s*人', flat)
                if size and (not item.get('company') or item['company'] in re.sub(r'\s+', '', text)):
                    item['company_size'] = re.sub(r'\s+', '', size.group(0))
                    break
        if not item.get('education') or not item.get('experience'):
            tags = [t.strip() for t in page.locator('.job-primary .info-primary p, .job-primary .info-primary .text, .job-info .text').all_inner_texts() if t.strip()]
            for tag in tags:
                if not item.get('education') and re.fullmatch(r'(学历不限|博士|硕士|本科|大专|高中|中专|初中)', tag):
                    item['education'] = tag
                if not item.get('experience') and re.fullmatch(r'(经验不限|\d+\s*[-–]\s*\d+\s*年|\d+年以上|在校/应届|应届生)', tag):
                    item['experience'] = tag
        return item

    def enrich(self, jobs, limit=20):
        return self._call(self._enrich, jobs, limit)

    def _enrich(self, jobs, limit=20):
        """Re-open existing job pages to fill facts the list card did not expose."""
        context = self._context()
        page = self._new_page()
        done = []
        try:
            for item in jobs[:max(1, min(int(limit), 40))]:
                try:
                    self._read_detail(page, item)
                    done.append(item)
                except Exception as exc:
                    done.append({'url': item.get('url', ''), 'error': str(exc).splitlines()[0][:200]})
                page.wait_for_timeout(700)
        finally:
            page.close()
            self._sweep()
        return done

    def submit(self, job, draft=''):
        return self._call(self._submit, job, draft)

    def _submit(self, job, draft):
        url = job.get('url', '')
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname != 'www.zhipin.com' or not re.fullmatch(r'/job_detail/[A-Za-z0-9_-]+\.html', parsed.path):
            return {'status': 'blocked', 'message': '仅接受 www.zhipin.com 的 HTTPS 岗位详情页。'}
        context = self._context()
        self._sweep(keep=1)
        page = self._new_page()
        clicked = False
        try:
            page.goto(url, wait_until='domcontentloaded')
            body = self._check(page)
            expected = re.sub(r'\s+', '', job.get('title', ''))
            normalized_body = re.sub(r'\s+', '', body)
            if not expected or expected not in normalized_body:
                return {'status': 'blocked', 'message': '岗位名称与页面不一致，停止操作。'}
            company = re.sub(r'\s+', '', str(job.get('company') or ''))
            if company and company not in normalized_body:
                return {'status': 'blocked', 'message': '公司名称与采集结果不一致，请重新核对岗位。'}
            salary = re.split('[·•]', str(job.get('salary') or ''))[0].strip()
            if salary and re.sub(r'\s+', '', salary) not in normalized_body:
                return {'status': 'blocked', 'message': '薪资与采集结果不一致，请重新分析并核对岗位。'}
            if page.get_by_text('继续沟通', exact=True).count():
                return {'status': 'blocked', 'message': '页面显示继续沟通，该岗位可能已联系，停止重复投递。'}
            button = page.get_by_role('link', name='立即沟通', exact=True)
            if not button.count():
                button = page.get_by_role('button', name='立即沟通', exact=True)
            if not button.count():
                button = page.get_by_text('立即沟通', exact=True)
            if button.count() != 1 or not button.is_visible():
                return {'status': 'blocked', 'message': '无法唯一确认立即沟通按钮，请手动检查登录状态和岗位页面。'}
            # Read the posting for a few seconds first, like a human would.
            page.wait_for_timeout(random.randint(2600, 5200))
            # Once dispatched, any exception counts as uncertain, including a click timeout.
            clicked = True
            button.click(timeout=10000)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                text = self._check(page)
                if any(x in text for x in ['打招呼成功', '已向BOSS发送', '已向Boss发送', '已发送打招呼']):
                    return {'status': 'sent', 'message': '页面确认 BOSS 打招呼成功（使用平台招呼语，未发送 PDF 附件）。', 'action': 'boss_greeting'}
                if page.get_by_text('继续沟通', exact=True).count():
                    return {'status': 'sent', 'message': '页面由立即沟通变为继续沟通，已确认发起联系；未发送 PDF 附件。', 'action': 'boss_greeting'}
                if any(x in text for x in ['今日沟通人数已达上限', '沟通人数已达上限']):
                    return {'status': 'blocked', 'message': 'BOSS 显示今日沟通人数达到上限。'}
                page.wait_for_timeout(400)
            return {'status': 'uncertain', 'message': '已点击沟通但未获得明确成功反馈，请人工核对，程序不会自动重试。'}
        except Exception as exc:
            return {'status': 'uncertain' if clicked else 'blocked', 'message': str(exc)[:500]}
        finally:
            # Keep uncertain pages for the user's inspection.
            if not clicked:
                page.close()

    def send_followup(self, company, text):
        return self._call(self._send_followup, company, text)

    def _send_followup(self, company, text):
        """After the platform greeting, post one detail message in that conversation."""
        context = self._context()
        page = self._new_page()
        try:
            self._goto(page, 'https://www.zhipin.com/web/geek/chat', timeout=30000)
            page.wait_for_timeout(2500)
            self._check(page)
            chats = page.locator('.chat-user, .geek-chat-item, .user-list li, .chat-list li')
            total = chats.count()
            if not total:
                raise RuntimeError('聊天列表为空，无法追发消息')
            target = None
            if company:
                for index in range(min(total, 20)):
                    item = chats.nth(index)
                    if company in (item.inner_text() or ''):
                        target = item
                        break
            target = target or chats.first
            target.click()
            page.wait_for_timeout(1500)
            editor = page.locator('div.chat-input[contenteditable="true"], [contenteditable="true"]').first
            # Pause before replying so the two messages do not land seconds apart.
            page.wait_for_timeout(random.randint(9000, 18000))
            editor.click()
            page.wait_for_timeout(random.randint(700, 1600))
            try:
                page.keyboard.type(text, delay=random.randint(28, 65))
            except Exception:
                page.keyboard.insert_text(text)
            page.wait_for_timeout(random.randint(1200, 2600))
            send = page.locator('button.btn-send').first
            if send.count() == 0 or not send.is_enabled():
                raise RuntimeError('发送按钮不可用，消息未发出')
            send.click()
            page.wait_for_timeout(2200)
            body = page.locator('body').inner_text(timeout=8000)
            ok = text[:12] in body
            return {'status': 'sent' if ok else 'uncertain',
                    'message': '招呼语补充消息已发送' if ok else '补充消息未确认，请人工核对'}
        finally:
            page.close()
            self._sweep(keep=0)

    def chat_preview(self, limit=15):
        return self._call(self._chat_preview, limit)

    def _chat_preview(self, limit=15):
        """Read the logged-in message list so sent greetings can be verified."""
        context = self._context()
        page = self._new_page()
        try:
            self._goto(page, 'https://www.zhipin.com/web/geek/chat', timeout=30000)
            page.wait_for_timeout(3000)
            body = page.locator('body').inner_text(timeout=10000)
            items = page.locator('.chat-user, .geek-chat-item, .user-list li, .chat-list li').all_inner_texts()
            return {'logged_in': '登录/注册' not in body, 'url': page.url,
                    'items': [re.sub(r'\s+', ' ', x).strip()[:120] for x in items[:limit]],
                    'preview': re.sub(r'\s+', ' ', body)[:300]}
        finally:
            page.close()
            self._sweep(keep=0)

    def close(self):
        try:
            self._call(self._close)
        except Exception:
            pass

    def _close(self):
        if self.connection is None and self.edge_endpoint:
            try:
                if self.playwright is None:
                    from playwright.sync_api import sync_playwright
                    self.playwright = sync_playwright().start()
                self.connection = self.playwright.chromium.connect_over_cdp(self.edge_endpoint, timeout=5000)
            except Exception:
                pass
        if self.connection is not None:
            try:
                if self.connection.is_connected():
                    self.connection.new_browser_cdp_session().send('Browser.close')
            except Exception:
                pass
        if self.playwright:
            self.playwright.stop()
        self.context = None
        self.connection = None
        self.playwright = None
        self.edge_endpoint = None


browser = BossBrowser()
