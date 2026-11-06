"""Exercise UI import → analyze → approve → simulate against an isolated database.
Never imports jobs into the user's workspace or invokes BOSS endpoints.
"""
import json
import os
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    with tempfile.TemporaryDirectory(prefix='job-pilot-flow-') as folder:
        os.environ['JOB_PILOT_DB'] = str(Path(folder) / 'flow.sqlite3')
        for name in ('JOB_PILOT_API_KEY', 'JOB_PILOT_BASE_URL', 'JOB_PILOT_MODEL'):
            os.environ.pop(name, None)
        import app as pilot
        # A real external action is a test failure, even if the UI accidentally enables live.
        def forbidden_browser():
            raise AssertionError('BOSS browser must never be used in this check')
        pilot._browser = forbidden_browser
        server = make_server('127.0.0.1', 0, pilot.app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        errors = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}', wait_until='networkidle')
                jobs = [{'title': 'AI应用开发工程师', 'company': 'UI隔离测试公司', 'city': '杭州', 'salary': '20-30K',
                         'description': 'Python LangGraph Agent MCP Redis 业务应用开发，参与项目架构设计。', 'url': 'https://www.zhipin.com/job_detail/UI_TEST_ONLY.html'}]
                page.locator('#fileInput').set_input_files({'name': 'flow.json', 'mimeType': 'application/json', 'buffer': json.dumps(jobs, ensure_ascii=False).encode()})
                page.wait_for_function("document.querySelector('#jobCount').textContent === '1'")
                page.locator('#analyzeAllBtn').click()
                page.wait_for_function("document.querySelector('.job-score')?.textContent.includes('/ 100')")
                page.locator('.job-row').click()
                page.locator('#jobDetail .primary-button').click()
                page.wait_for_function("document.querySelector('.job-tag')?.textContent.includes('审核入队')")
                page.locator('label').filter(has=page.locator('#enabledToggle')).click()
                page.locator('#saveRulesBtn').click()
                page.wait_for_function("document.querySelector('#automationTitle').textContent.includes('模拟托管已启用')")
                page.locator('#runBtn').click()
                page.wait_for_function("document.querySelector('.job-tag')?.textContent.includes('模拟完成')")
                job = pilot.engine._job(1)
                assert job['status'] == 'simulated' and job['attempt']['mode'] == 'dry_run'
                assert pilot.engine.day_usage('live') == 0
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=3)
    print('UI flow passed: isolated import, analysis, review queue, simulated dispatch; no external browser action.')


if __name__ == '__main__':
    main()
