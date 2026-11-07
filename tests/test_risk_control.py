"""Risk control must stop the queue and surface an alert, never be treated as a soft miss."""
import pytest

import app
from engine import JobEngine


class ChallengedBrowser:
    def __init__(self, error):
        self.error = error

    def submit(self, job, draft):
        raise self.error


def build(tmp_path, monkeypatch, browser):
    engine = JobEngine(str(tmp_path / 'risk.sqlite'))
    engine.set_profile('Python Agent')
    engine.set_rules({'cities': ['杭州'], 'titles': ['AI'], 'min_salary': 20, 'max_salary': 30, 'skills': ['Python']})
    engine.import_jobs([{'external_id': 'a', 'title': 'AI应用开发', 'city': '杭州',
                         'salary': '20-30K', 'description': 'Python Agent 开发'}])
    engine.analyze()
    engine.approve(1)
    engine.set_automation({'enabled': True, 'mode': 'live', 'daily_limit': 10,
                           'interval_seconds': 60, 'min_score': 0, 'auto_approve': False,
                           'auto_collect': False})
    monkeypatch.setattr(app, 'engine', engine)
    monkeypatch.setattr(app, '_browser', lambda: browser)
    return engine


def test_captcha_stops_automation_and_alerts(tmp_path, monkeypatch):
    browser = ChallengedBrowser(RuntimeError('BOSS 要求安全验证，请到浏览器手动完成，程序不会绕过验证。'))
    engine = build(tmp_path, monkeypatch, browser)

    result = app.run_once()

    assert result['processed'] == 1
    assert result['outcomes'][0]['status'] == 'blocked'
    assert engine.get_automation()['enabled'] is False
    alerts = [row for row in engine.state()['alerts']]
    assert alerts and '安全验证' in alerts[0]['detail']


def test_random_browser_error_stays_soft(tmp_path, monkeypatch):
    browser = ChallengedBrowser(RuntimeError('Page.goto: Timeout 30000ms exceeded'))
    engine = build(tmp_path, monkeypatch, browser)

    result = app.run_once()

    assert result['outcomes'][0]['status'] == 'uncertain'
    assert engine.get_automation()['enabled'] is True


def test_enabling_live_requires_a_logged_in_session(tmp_path, monkeypatch):
    engine = JobEngine(str(tmp_path / 'login.sqlite'))
    monkeypatch.setattr(app, 'engine', engine)

    class LoggedOut:
        def check_login(self):
            return {'logged_in': False, 'challenge': False, 'reason': '未检测到登录态，请先在投递用的 Chrome 窗口扫码登录'}

    monkeypatch.setattr(app, '_browser', lambda: LoggedOut())
    client = app.app.test_client()
    response = client.post('/api/automation', json={'enabled': True, 'mode': 'live'})
    assert response.status_code == 409
    assert engine.get_automation()['enabled'] is False

    class LoggedIn(LoggedOut):
        def check_login(self):
            return {'logged_in': True, 'challenge': False, 'reason': ''}

    monkeypatch.setattr(app, '_browser', lambda: LoggedIn())
    response = client.post('/api/automation', json={'enabled': True, 'mode': 'live'})
    assert response.status_code == 200
    assert engine.get_automation()['enabled'] is True
