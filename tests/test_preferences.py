import pytest

from engine import JobEngine, ValidationError


def make(tmp_path):
    return JobEngine(str(tmp_path / 'preferences.sqlite'))


def base(**extra):
    value = {'title': '后端工程师', 'salary': '20K', 'company_size': '100-499',
             'education': '本科', 'experience': '3-5年', 'recruitment_type': 'social'}
    value.update(extra)
    return value


def test_rules_validate_and_match_company_boundaries(tmp_path):
    e = make(tmp_path)
    e.set_rules({'company_min': 100, 'company_max': 1000,
                 'recruitment_type': 'social', 'max_education': '硕士'})
    assert e.match_job(base(company_size='100-499'), '', e.get_rules()['data'])[0] >= 0
    assert e.match_job(base(company_size='500-999'), '', e.get_rules()['data'])[0] >= 0
    assert e.match_job(base(company_size='20-99'), '', e.get_rules()['data'])[0] == -1
    assert e.match_job(base(company_size='1000-9999'), '', e.get_rules()['data'])[0] == -1
    unknown_score, unknown_reason = e.match_job(base(company_size=''), '', e.get_rules()['data'])
    assert unknown_score >= 0 and '公司规模待核验' in unknown_reason


def test_social_and_education_hard_filters(tmp_path):
    e = make(tmp_path)
    rules = {'company_min': 100, 'company_max': 1000,
             'recruitment_type': 'social', 'max_education': '硕士'}
    assert e.match_job(base(recruitment_type='校招'), '', rules)[0] == -1
    assert e.match_job(base(recruitment_type='', experience='经验不限'), '', rules)[0] >= 0
    assert '人工核对' in e.match_job(base(recruitment_type='', experience=''), '', rules)[1]
    assert e.match_job(base(education='博士'), '', rules)[0] == -1
    assert e.match_job(base(education='硕士及以下'), '', rules)[0] >= 0
    assert e.match_job(base(education='本科及以上'), '', rules)[0] >= 0
    assert e.match_job(base(education='博士/硕士'), '', rules)[0] >= 0
    assert e.match_job(base(education='不限/博士'), '', rules)[0] == -1
    unlimited = dict(rules, max_education='不限')
    assert e.match_job(base(education='博士'), '', unlimited)[0] >= 0
    assert '人工核对' in e.match_job(base(education=''), '', rules)[1]
    assert e.match_job(base(title='校园招聘后端'), '', rules)[0] == -1
    assert e.match_job(base(description='负责后端开发并指导实习生'), '', rules)[0] >= 0
    assert e.match_job(base(description='本岗位仅面向在校学生招聘'), '', rules)[0] == -1


def test_duplicate_import_fills_empty_facts_and_invalidates_review(tmp_path):
    e = make(tmp_path)
    e.import_jobs([{'external_id': 'same', 'title': '后端', 'salary': '20K'}])
    e.analyze(1)
    e.approve(1, 'hi')
    assert e.import_jobs([{'external_id': 'same', 'title': '后端', 'company_size': '100-499',
                           'education': '本科', 'experience': '3-5年', 'recruitment_type': 'social'}]) == {
        'added': 0, 'total': 1, 'duplicates': 1}
    job = e._job(1)
    assert job['company_size'] == '100-499'
    assert job['education'] == '本科'
    assert job['score'] is None and job['status'] == 'new' and not job['approved']
    e.import_jobs([{'external_id': 'same', 'title': '后端', 'education': '博士'}])
    assert e._job(1)['education'] == '本科'


def test_invalid_preference_values(tmp_path):
    e = make(tmp_path)
    with pytest.raises(ValidationError):
        e.set_rules({'recruitment_type': 'campus'})
    with pytest.raises(ValidationError):
        e.set_rules({'max_education': '博士后'})
    with pytest.raises(ValidationError):
        e.set_rules({'company_min': 1000, 'company_max': 100})
    e.set_rules({'company_min': 100, 'company_max': 1000, 'recruitment_type': 'social', 'max_education': '硕士'})
    e.set_rules({'company_min': None, 'company_max': '', 'recruitment_type': '', 'max_education': None})
    assert not {'company_min', 'company_max', 'recruitment_type', 'max_education'}.intersection(e.get_rules()['data'])


def test_outsourcing_and_staffing_agencies_are_rejected(tmp_path):
    e = make(tmp_path)
    e.set_rules({})
    rules = e.get_rules()['data']
    assert e.match_job(base(company='科锐国际'), '', rules)[0] == -1
    assert e.match_job(base(company='外企德科'), '', rules)[0] == -1
    assert e.match_job(base(description='长期驻场客户现场，人力外包岗位'), '', rules)[0] == -1
    assert e.match_job(base(description='自研产品，非外包，不驻场'), '', rules)[0] >= 0


def test_non_engineering_titles_are_excluded(tmp_path):
    e = make(tmp_path)
    e.set_rules({'titles': ['AI', 'Agent'], 'exclude_titles': ['产品经理', '销售']})
    rules = e.get_rules()['data']
    assert e.match_job(base(title='AI Agent平台产品经理'), '', rules)[0] == -1
    assert e.match_job(base(title='Agent研发工程师'), '', rules)[0] >= 0


def test_soft_campus_wording_does_not_block(tmp_path):
    """"可校招 / 接受应届" still hires experienced people; only campus-only wording blocks."""
    e = make(tmp_path)
    e.set_rules({'recruitment_type': 'social', 'titles': ['AI', 'Agent']})
    rules = e.get_rules()['data']
    assert e.match_job(base(title='可校招-AI Agent研发工程师', experience='1-3年'), '', rules)[0] >= 0
    assert e.match_job(base(title='AI Agent工程师（接受应届）', experience='3-5年'), '', rules)[0] >= 0
    assert e.match_job(base(title='AI Agent工程师', experience='在校/应届'), '', rules)[0] == -1
    assert e.match_job(base(title='【2027校招】AI Agent开发', experience='经验不限'), '', rules)[0] == -1


def test_large_staffing_vendors_are_treated_as_outsourcing(tmp_path):
    e = make(tmp_path)
    e.set_rules({'titles': ['AI', 'Python']})
    rules = e.get_rules()['data']
    for company in ('北京软通动力云计', '中软国际', '博彦科技', '文思海辉'):
        score, reason = e.match_job(base(title='AI应用开发', company=company), '', rules)
        assert score == -1 and '外包' in reason, company


def test_tiny_company_needs_funding_and_large_needs_foreign(tmp_path):
    e = make(tmp_path)
    e.set_rules({'titles': ['AI', 'Agent'], 'company_min': 0, 'company_max': 9999,
                 'tiny_needs_funding': True, 'large_needs_foreign': True})
    rules = e.get_rules()['data']
    tiny = base(company_size='0-20人', title='AI Agent工程师')
    assert e.match_job(tiny, '', rules)[0] == -1
    assert '融资' in e.match_job(tiny, '', rules)[1]
    assert e.match_job({**tiny, 'financing': 'A轮'}, '', rules)[0] >= 0
    assert e.match_job({**tiny, 'financing': '未融资'}, '', rules)[0] == -1
    big = base(company_size='1000-9999人', title='AI Agent工程师')
    assert e.match_job(big, '', rules)[0] == -1
    assert '外资' in e.match_job(big, '', rules)[1]
    assert e.match_job({**big, 'company_type': '外商独资'}, '', rules)[0] >= 0
    assert e.match_job(base(company_size='500-999人', title='AI Agent工程师'), '', rules)[0] >= 0


def test_salary_range_only_needs_an_intersection(tmp_path):
    e = make(tmp_path)
    e.set_rules({'min_salary': 20, 'max_salary': 30, 'titles': ['AI', 'Agent']})
    rules = e.get_rules()['data']
    for salary in ('18-30K', '18-25K', '15-24K', '20-30K', '30-45K', '25K', '30-60K'):
        assert e.match_job(base(title='AI Agent工程师', salary=salary), '', rules)[0] >= 0, salary
    for salary in ('8-12K', '35-60K', '15-19K', '40-70K'):
        score, reason = e.match_job(base(title='AI Agent工程师', salary=salary), '', rules)
        assert score == -1 and '薪资区间' in reason, salary

