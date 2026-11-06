import json
from types import SimpleNamespace

import app
from engine import JobEngine


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


def make_engine(tmp_path):
    engine = JobEngine(str(tmp_path / "api.sqlite"))
    engine.set_profile("Python Agent LangGraph")
    engine.set_rules({"cities": ["杭州"], "titles": ["AI"], "min_salary": 20, "skills": ["Python", "Agent"]})
    engine.import_jobs([{"external_id": "api-job", "title": "AI", "city": "杭州", "salary": "20K", "description": "完整 JD：Python Agent 开发"}])
    return engine


def test_write_routes_reject_bad_origin_host_and_json(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "engine", make_engine(tmp_path))
    client = app.app.test_client()
    assert client.post("/api/rules", json={}, headers={"Origin": "http://localhost.evil.com"}).status_code == 403
    assert client.post("/api/rules", json={}, base_url="http://evil.example").status_code == 403
    response = client.post("/api/rules", data="not-json", content_type="application/json")
    assert response.status_code == 400 and "error" in response.get_json()


def test_ai_mock_analysis_returns_valid_score(tmp_path, monkeypatch):
    engine = make_engine(tmp_path)
    monkeypatch.setattr(app, "engine", engine)
    for key, value in {"JOB_PILOT_API_KEY": "test", "JOB_PILOT_BASE_URL": "http://llm.test/v1", "JOB_PILOT_MODEL": "mock"}.items():
        monkeypatch.setenv(key, value)
    payload = {"score": 88, "reason": "技能与岗位匹配", "risks": [], "missing_skills": [], "draft": "您好，期待沟通。"}
    monkeypatch.setattr(app.requests, "post", lambda *a, **k: FakeResponse(json.dumps(payload, ensure_ascii=False)))
    response = app.app.test_client().post("/api/analyze", json={"id": 1})
    assert response.status_code == 200
    job = response.get_json()["jobs"]
    assert job["score"] == 88 and job["analysis_source"] == "ai"


def test_bad_ai_json_falls_back_to_local_review(tmp_path, monkeypatch):
    engine = make_engine(tmp_path)
    monkeypatch.setattr(app, "engine", engine)
    for key, value in {"JOB_PILOT_API_KEY": "test", "JOB_PILOT_BASE_URL": "http://llm.test/v1", "JOB_PILOT_MODEL": "mock"}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(app.requests, "post", lambda *a, **k: FakeResponse("{bad json"))
    response = app.app.test_client().post("/api/analyze", json={"id": 1})
    assert response.status_code == 200
    job = response.get_json()["jobs"]
    assert job["analysis_source"] == "local_fallback"
    assert job["approved"] is False
