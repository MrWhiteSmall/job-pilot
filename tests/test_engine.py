import pytest

from engine import JobEngine


def make(tmp_path):
    return JobEngine(str(tmp_path / "x.sqlite"))


def test_hard_filters_and_title_scope(tmp_path):
    e = make(tmp_path)
    rules = {"cities": ["杭州"], "titles": ["AI应用", "Agent"], "blacklist": ["外包"], "min_salary": 20, "skills": ["Python", "LangGraph"]}
    good = {"title": "AI应用开发工程师", "city": "杭州", "salary": "20-30K", "description": "外包"}
    assert e.match_job(good, "Python LangGraph", rules)[0] == -1
    good["description"] = "Python LangGraph"
    assert e.match_job(good, "Python LangGraph", rules)[0] >= 0
    wrong = {"title": "后端工程师", "city": "杭州", "salary": "20-30K", "description": "AI应用"}
    assert e.match_job(wrong, "Python", rules)[0] == -1


def test_url_dedup_and_missing_salary(tmp_path):
    e = make(tmp_path)
    jobs = [{"title": "AI", "url": "https://www.zhipin.com/job/abc?securityId=x&lid=1"}, {"title": "AI", "url": "https://www.zhipin.com/job/abc?securityId=y&lid=2"}]
    assert e.import_jobs(jobs)["added"] == 1
    # Unknown salary no longer blocks the job: it must stay visible with a 待核验 note.
    score, reason = e.match_job(jobs[0], "", {"cities": []})
    assert score >= 0 and '薪资未公开显示' in reason


def test_approval_and_daily_queue(tmp_path):
    e = make(tmp_path)
    e.set_rules({"cities": [], "skills": []})
    e.import_jobs([{ "external_id": "a", "title": "AI", "salary": "20K" }, {"external_id": "b", "title": "AI", "salary": "20K"}])
    e.analyze(); e.approve(1, "hi"); e.approve(2, "hi")
    assert len(e.queue(0)) == 2
    e.set_automation({"enabled": True, "mode": "dry_run", "daily_limit": 1, "interval_seconds": 60, "min_score": 0})


def test_dry_run_does_not_block_live(tmp_path):
    e = make(tmp_path)
    e.import_jobs([{ "external_id": "a", "title": "AI", "salary": "20K" }]); e.analyze(); e.approve(1, "hi")
    e.record_attempt(1, "dry_run", "simulated")
    assert len(e.queue(0)) == 1
    e.record_attempt(1, "live", "uncertain")
    assert len(e.queue(0)) == 0


def test_terminal_status_survives_reanalyze(tmp_path):
    e = make(tmp_path)
    e.import_jobs([{ "external_id": "a", "title": "AI", "salary": "20K" }]); e.analyze()
    with e._connect() as db: db.execute("UPDATE jobs SET status='sent' WHERE id=1")
    e.analyze(1)
    assert e._job(1)["status"] == "sent"
