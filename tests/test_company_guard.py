"""Same employer, several postings: only the first conversation should be opened."""
import pytest

from engine import JobEngine


def make(tmp_path):
    engine = JobEngine(str(tmp_path / 'company.sqlite'))
    engine.set_profile('Python LangGraph Agent MCP')
    engine.set_rules({'cities': [], 'titles': ['AI'], 'skills': ['Python', 'Agent'],
                      'min_salary': 20, 'max_salary': 30})
    return engine


def posting(job_id, company, title='AI应用开发工程师'):
    return {'external_id': job_id, 'title': title, 'company': company, 'city': '杭州',
            'salary': '20-30K', 'description': 'Python Agent LangGraph 开发'}


def test_second_posting_from_contacted_company_is_not_queued(tmp_path):
    engine = make(tmp_path)
    engine.import_jobs([posting('a1', '华是互娱'), posting('a2', '华是互娱', 'AI 全栈开发工程师（Java/React）')])
    engine.analyze()
    engine.approve(1)
    engine.approve(2)
    assert len(engine.queue(0)) == 2  # nothing contacted yet, both are legitimate candidates

    engine.record_attempt(1, 'live', 'pending')
    engine.finish_attempt(1, 'sent', '页面由立即沟通变为继续沟通')
    assert engine.queue(0) == []  # same company must not be greeted twice

    assert '华是互娱' in engine.contacted_companies()


def test_company_guard_ignores_spacing_and_other_companies(tmp_path):
    engine = make(tmp_path)
    engine.import_jobs([posting('b1', '橙 宁'), posting('b2', '橙宁'),
                        posting('c1', '别的公司')])
    engine.analyze()
    for job in engine.state()['jobs']:
        engine.approve(job['id'])
    engine.record_attempt(1, 'live', 'pending')
    engine.finish_attempt(1, 'blocked', '页面显示继续沟通，该岗位可能已联系')

    remaining = {job['data']['company'] for job in engine.queue(0)}
    assert remaining == {'别的公司'}


def test_skip_marks_job_rejected_with_reason(tmp_path):
    engine = make(tmp_path)
    engine.import_jobs([posting('d1', '某公司')])
    engine.analyze()
    engine.skip(1, '同一公司 30 天内已沟通，跳过重复投递')
    job = engine.state()['jobs'][0]
    assert job['status'] == 'rejected'
    assert '已沟通' in job['reason']
