import threading
from datetime import datetime, timedelta, timezone

import app
from engine import JobEngine


class FakeBrowser:
    def __init__(self, status="sent", message="ok"):
        self.calls = []
        self.status = status
        self.message = message

    def submit(self, job, draft):
        self.calls.append((job, draft))
        return {"status": self.status, "message": self.message}


def setup_engine(tmp_path, jobs, *, approved=True, score=80):
    engine = JobEngine(str(tmp_path / "automation.sqlite"))
    engine.set_rules({"cities": ["杭州"], "titles": ["AI"], "min_salary": 20, "skills": []})
    engine.import_jobs(jobs)
    engine.analyze()
    if approved:
        for jid in range(1, len(jobs) + 1):
            engine.approve(jid, "您好，期待沟通。")
    with engine._connect() as db:
        db.execute("UPDATE jobs SET score=? WHERE id<=?", (score, len(jobs)))
    return engine


def configure(monkeypatch, engine, *, enabled=True, mode="dry_run", limit=10, interval=None, min_score=60, auto_approve=False):
    monkeypatch.setattr(app, "engine", engine)
    if interval is None:
        interval = 10 if mode == "dry_run" else 60
    engine.set_automation({"enabled": enabled, "mode": mode, "daily_limit": limit, "interval_seconds": interval,
                           "min_score": min_score, "auto_approve": auto_approve, "auto_collect": False})


def test_paused_does_not_run(tmp_path, monkeypatch):
    engine = setup_engine(tmp_path, [{"external_id": "a", "title": "AI", "city": "杭州", "salary": "20K"}])
    configure(monkeypatch, engine, enabled=False)
    result = app.run_once()
    assert result["status"] == "paused" and result["processed"] == 0


def test_only_approved_and_one_item_are_sent(tmp_path, monkeypatch):
    jobs = [{"external_id": "a", "title": "AI", "city": "杭州", "salary": "20K"}, {"external_id": "b", "title": "AI", "city": "杭州", "salary": "20K"}]
    engine = setup_engine(tmp_path, jobs, approved=False)
    engine.approve(1, "已审核招呼语")
    configure(monkeypatch, engine, mode="live")
    browser = FakeBrowser(); monkeypatch.setattr(app, "_browser", lambda: browser)
    result = app.run_once()
    assert result["processed"] == 1 and len(browser.calls) == 1
    assert browser.calls[0][1] == "已审核招呼语"


def test_daily_limit_counts_current_live_attempts_even_if_old(tmp_path, monkeypatch):
    jobs = [{"external_id": str(i), "title": "AI", "city": "杭州", "salary": "20K"} for i in range(3)]
    engine = setup_engine(tmp_path, jobs)
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    with engine._connect() as db:
        db.execute("INSERT INTO attempts(job_id,mode,outcome,detail,created_at) VALUES(?,?,?,?,?)", (1, "live", "sent", "old", old))
    configure(monkeypatch, engine, mode="live", limit=2)
    browser = FakeBrowser(); monkeypatch.setattr(app, "_browser", lambda: browser)
    result = app.run_once()
    assert result["processed"] == 1 and len(browser.calls) == 1


def test_auto_approve_dry_run_processes_threshold_job(tmp_path, monkeypatch):
    engine = setup_engine(tmp_path, [{"external_id": "a", "title": "AI", "city": "杭州", "salary": "20K", "description": "Python Agent开发岗位，负责业务研发"}], approved=False)
    configure(monkeypatch, engine, auto_approve=True, mode="dry_run")
    browser = FakeBrowser(); monkeypatch.setattr(app, "_browser", lambda: browser)
    result = app.run_once()
    assert result["processed"] == 1 and result["outcomes"][0]["status"] == "simulated"
    assert browser.calls == []


def test_list_summary_is_not_auto_approved(tmp_path, monkeypatch):
    engine = setup_engine(tmp_path, [{"external_id": "summary", "title": "AI", "city": "杭州", "salary": "20K", "description": "【列表摘要】Python Agent开发岗位"}], approved=False)
    configure(monkeypatch, engine, auto_approve=True, mode="dry_run")
    assert app.run_once()["processed"] == 0
    assert engine._job(1)["approved"] is False
def test_platform_stop_pauses_but_single_uncertain_keeps_queue(tmp_path, monkeypatch):
    engine = setup_engine(tmp_path / "blocked", [{"external_id": "limit", "title": "AI", "city": "杭州", "salary": "20K"}])
    configure(monkeypatch, engine, mode="live")
    browser = FakeBrowser("blocked", message="BOSS 显示今日沟通人数达到上限")
    monkeypatch.setattr(app, "_browser", lambda: browser)
    assert app.run_once()["processed"] == 1
    second = app.run_once()
    assert second["status"] == "paused" and second["processed"] == 0
    assert len(browser.calls) == 1

    engine = setup_engine(tmp_path / "uncertain", [{"external_id": "uncertain", "title": "AI", "city": "杭州", "salary": "20K"}])
    configure(monkeypatch, engine, mode="live", interval=60)
    browser = FakeBrowser("uncertain")
    monkeypatch.setattr(app, "_browser", lambda: browser)
    assert app.run_once()["processed"] == 1
    assert engine.get_automation()["enabled"] is True
    second = app.run_once()
    assert second["status"] in ("idle", "interval")
    assert len(browser.calls) == 1


def test_profile_or_rules_change_revokes_approval(tmp_path, monkeypatch):
    engine = setup_engine(tmp_path, [{"external_id": "a", "title": "AI", "city": "杭州", "salary": "20K"}])
    engine.set_profile("旧简历")
    engine.approve(1, "旧简历审核通过")
    engine.set_profile("换了一份新简历")
    assert engine._job(1)["approved"] is False
    engine.analyze(1)
    engine.approve(1, "重新审核")
    engine.set_rules({"cities": ["上海"]})
    assert engine._job(1)["approved"] is False


def test_restart_defaults_to_paused(tmp_path):
    """新建引擎不能顺手停掉正在跑的托管（工具脚本会误杀投递）。"""
    db = str(tmp_path / "restart.sqlite")
    first = JobEngine(db)
    first.set_automation({"enabled": True, "mode": "dry_run", "interval_seconds": 10})
    second = JobEngine(db)
    assert second.get_automation()["enabled"] is True
    # 「重启即暂停」由 app.py 启动流程显式调用。
    second.set_automation({"enabled": False})
    assert JobEngine(db).get_automation()["enabled"] is False


def test_hard_filter_rejects_before_ai(tmp_path, monkeypatch):
    engine = JobEngine(str(tmp_path / "reject.sqlite"))
    engine.set_rules({"cities": ["杭州"], "titles": ["AI"], "min_salary": 20})
    engine.import_jobs([{ "external_id": "bad", "title": "AI", "city": "上海", "salary": "20K" }])
    calls = []
    def fake_ai(job, resume):
        calls.append(job); raise AssertionError("硬筛失败岗位不得调用 AI")
    monkeypatch.setattr(app, "analyzer", lambda: fake_ai)
    configure(monkeypatch, engine, auto_approve=True, mode="dry_run")
    assert app.run_once()["processed"] == 0
    assert calls == []


def test_worker_returns_stoppable_thread(tmp_path, monkeypatch):
    engine = setup_engine(tmp_path, [{"external_id": "a", "title": "AI", "city": "杭州", "salary": "20K"}])
    configure(monkeypatch, engine, mode="dry_run")
    monkeypatch.setattr(app, "_browser", lambda: FakeBrowser())
    stop_event = threading.Event(); thread = app.start_worker(stop_event)
    assert thread.is_alive(); stop_event.set(); thread.join(timeout=3); assert not thread.is_alive()
