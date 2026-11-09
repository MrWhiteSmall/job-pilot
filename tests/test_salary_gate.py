import app
from tests.test_automation import FakeBrowser, configure, setup_engine


def make_engine(tmp_path):
    engine = setup_engine(
        tmp_path,
        [{"external_id": "nosalary", "title": "AI 应用开发", "city": "杭州", "salary": "",
          "description": "负责 AI 应用开发，Python / Agent"}],
        approved=False,
    )
    engine.set_profile("Python Agent 后端开发，LangGraph")
    rules = engine.get_rules()["data"]
    engine.set_rules({**rules, "skills": ["Python", "Agent", "LangGraph", "后端"]})
    engine.analyze()
    engine.approve(1)
    return engine


class NoSalaryBrowser(FakeBrowser):
    def __init__(self):
        super().__init__(status="sent", message="ok")
        self.enriched = []

    def enrich(self, jobs, limit):
        self.enriched.append(len(jobs))
        return []


def test_live_holds_job_without_salary(tmp_path, monkeypatch):
    engine = make_engine(tmp_path)
    configure(monkeypatch, engine, mode="live", min_score=60)
    fake = NoSalaryBrowser()
    monkeypatch.setattr(app, "_browser", lambda: fake)
    app._salary_hold.clear()

    result = app.run_once()

    assert result["status"] == "needs_salary"
    assert fake.calls == []
    assert fake.enriched == [1]
    with engine._connect() as db:
        attempts = db.execute("SELECT COUNT(*) AS n FROM attempts").fetchone()["n"]
    assert attempts == 0


def test_live_sends_after_salary_is_filled(tmp_path, monkeypatch):
    engine = make_engine(tmp_path)
    configure(monkeypatch, engine, mode="live", min_score=60)

    class FillingBrowser(FakeBrowser):
        def enrich(self, jobs, limit):
            return [{**jobs[0], "salary": "25-35K", "error": None}]

    fake = FillingBrowser()
    monkeypatch.setattr(app, "_browser", lambda: fake)
    app._salary_hold.clear()

    result = app.run_once()

    assert result["status"] == "done" and result["outcomes"][0]["status"] == "sent"
    assert len(fake.calls) == 1
