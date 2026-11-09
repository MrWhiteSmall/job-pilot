"""实验分支的离线测试：不启动浏览器、不联网、不碰主数据库。"""
import json
from datetime import datetime

import pytest

from branch import company_hunt, careers_probe

COMPANY_HTML = """
<div class="company-list">
  <div class="company-card">
    <a href="/gongsi/abc123.html?ka=company-card" class="company-info">
      <h3 class="company-name">杭州云枢智能科技有限公司</h3>
      <ul class="company-tags">
        <li>人工智能</li>
        <li>100-499人</li>
        <li>B轮</li>
      </ul>
    </a>
  </div>
  <div class="company-card">
    <a href="/gongsi/abc123.html?ka=duplicate" class="company-info">
      <h3 class="company-name">杭州云枢智能科技有限公司</h3>
      <ul class="company-tags"><li>人工智能</li><li>100-499人</li><li>B轮</li></ul>
    </a>
  </div>
  <div class="company-card">
    <a href="https://www.zhipin.com/gongsi/def456.html?ka=company-card">
      <h3 class="company-name">杭州拾光数据服务有限公司</h3>
      <ul class="company-tags">
        <li>企业服务</li>
        <li>500-999人</li>
        <li>已上市</li>
      </ul>
    </a>
  </div>
  <div class="company-card">
    <a href="/gongsi/ghi789.html" class="company-info">
      <h3 class="company-name">杭州知行网络科技有限公司</h3>
      <ul class="company-tags"><li>互联网</li></ul>
    </a>
  </div>
</div>
"""

JOB_HTML = """
<ul class="job-list">
  <li class="job-card">
    <a href="/job_detail/aaa.html?lid=1" title="AI Agent 工程师">
      <div class="job-title"><span class="job-name">AI Agent 工程师</span></div>
      <span class="salary">25-40K·14薪</span>
      <span class="job-area">杭州·西湖区</span>
    </a>
  </li>
  <li class="job-card">
    <a href="/job_detail/bbb.html">
      <h3>Python 后端开发工程师</h3>
      <span class="red">20-35K</span>
      <span class="job-area">杭州·滨江区</span>
    </a>
  </li>
</ul>
"""


class FakePage:
    def __init__(self, html):
        self._html = html
        self.closed = False

    def inner_html(self, selector):
        assert selector == 'body'
        return self._html

    def close(self):
        self.closed = True


class FakeBrowser:
    """只有 company_hunt 需要的四个鸭子类型方法。"""

    def __init__(self, htmls):
        self._htmls = list(htmls)
        self.pages = []
        self.visited = []
        self.sweeps = 0

    def _new_page(self):
        html = self._htmls.pop(0) if self._htmls else '<html></html>'
        page = FakePage(html)
        self.pages.append(page)
        return page

    def _goto(self, page, url, timeout=None):
        self.visited.append(url)
        return page

    def _check(self, page):
        return page.inner_html('body')

    def _sweep(self):
        self.sweeps += 1


# ---------------------------------------------------------------- company_hunt


def test_parse_company_cards_fields_dedupe_and_missing():
    cards = company_hunt.parse_company_cards(COMPANY_HTML)

    assert len(cards) == 3  # 重复卡片按公司名去重
    assert cards[0] == {
        'name': '杭州云枢智能科技有限公司',
        'industry': '人工智能',
        'size': '100-499人',
        'funding': 'B轮',
        'url': 'https://www.zhipin.com/gongsi/abc123.html',
    }
    assert cards[1]['name'] == '杭州拾光数据服务有限公司'
    assert cards[1]['size'] == '500-999人'
    assert cards[1]['funding'] == '已上市'
    # 缺字段留空，不猜
    assert cards[2]['name'] == '杭州知行网络科技有限公司'
    assert cards[2]['industry'] == '互联网'
    assert cards[2]['size'] == ''
    assert cards[2]['funding'] == ''


def test_parse_company_cards_empty_and_garbage():
    assert company_hunt.parse_company_cards('') == []
    assert company_hunt.parse_company_cards('<div>没有公司卡片</div>') == []


def test_parse_company_cards_falls_back_to_anchor_title():
    html = '<a href="/gongsi/xyz.html" title="杭州乙科技有限公司">查看详情</a>'
    cards = company_hunt.parse_company_cards(html)

    assert len(cards) == 1
    assert cards[0]['name'] == '杭州乙科技有限公司'
    assert cards[0]['url'] == 'https://www.zhipin.com/gongsi/xyz.html'
    assert cards[0]['industry'] == ''
    assert cards[0]['size'] == ''
    assert cards[0]['funding'] == ''


def test_parse_company_cards_does_not_use_view_details_as_name():
    html = (
        '<div class="company-card"><a href="/gongsi/xyz.html">'
        '查看详情</a></div>'
    )
    cards = company_hunt.parse_company_cards(html)

    assert len(cards) == 1
    assert cards[0]['name'] == ''
    assert cards[0]['url'] == 'https://www.zhipin.com/gongsi/xyz.html'


def test_parse_job_cards_fields():
    jobs = company_hunt.parse_job_cards(JOB_HTML)

    assert len(jobs) == 2
    assert jobs[0]['title'] == 'AI Agent 工程师'
    assert jobs[0]['salary'] == '25-40K·14薪'
    assert jobs[0]['city'] == '杭州'
    assert jobs[0]['url'] == 'https://www.zhipin.com/job_detail/aaa.html'


def test_parse_company_site_prefers_external_official_site():
    html = (
        '<a href="https://www.zhipin.com/gongsi/x.html">官网</a>'
        '<a href="http://www.acme-ai.com" target="_blank">官网</a>'
    )
    assert company_hunt.parse_company_site(html) == 'http://www.acme-ai.com'
    assert company_hunt.parse_company_site('<div>无官网</div>') == ''


def test_discover_companies_requires_browser():
    with pytest.raises(RuntimeError, match='需要传入 browser'):
        company_hunt.discover_companies(limit=1)


def test_discover_companies_limit_dedupe_and_cleanup():
    browser = FakeBrowser([COMPANY_HTML])

    companies = company_hunt.discover_companies(limit=1, browser=browser)

    assert [card['name'] for card in companies] == ['杭州云枢智能科技有限公司']
    assert len(browser.visited) == 1
    assert 'city=101210100' in browser.visited[0]
    assert 'page=1' in browser.visited[0]
    assert browser.sweeps == 1
    assert browser.pages[0].closed is True


def test_discover_companies_pages_until_limit():
    page_one = """
    <div class="company-card"><a href="/gongsi/a.html">
      <h3 class="company-name">杭州甲公司</h3><ul class="company-tags"><li>互联网</li></ul>
    </a></div>
    <div class="company-card"><a href="/gongsi/a2.html">
      <h3 class="company-name">杭州甲公司</h3><ul class="company-tags"><li>互联网</li></ul>
    </a></div>
    """
    page_two = """
    <div class="company-card"><a href="/gongsi/a3.html">
      <h3 class="company-name">杭州甲公司</h3><ul class="company-tags"><li>互联网</li></ul>
    </a></div>
    <div class="company-card"><a href="/gongsi/b.html">
      <h3 class="company-name">杭州乙公司</h3><ul class="company-tags"><li>企业服务</li></ul>
    </a></div>
    """
    browser = FakeBrowser([page_one, page_two])

    companies = company_hunt.discover_companies(limit=2, browser=browser)

    assert [card['name'] for card in companies] == ['杭州甲公司', '杭州乙公司']
    assert len(browser.visited) == 2
    assert 'page=2' in browser.visited[1]


def test_list_company_jobs_uses_browser_and_closes_page():
    browser = FakeBrowser([JOB_HTML])

    jobs = company_hunt.list_company_jobs(
        'https://www.zhipin.com/gongsi/abc123.html', browser
    )

    assert [job['title'] for job in jobs] == ['AI Agent 工程师', 'Python 后端开发工程师']
    assert browser.visited == ['https://www.zhipin.com/gongsi/abc123.html']
    assert browser.pages[0].closed is True


def test_company_report_without_probe_site():
    browser = FakeBrowser([COMPANY_HTML, JOB_HTML])

    report = company_hunt.company_report(limit=1, browser=browser, probe_site=False)

    assert set(report) == {'generated_at', 'companies'}
    datetime.fromisoformat(report['generated_at'])
    company = report['companies'][0]
    assert company['name'] == '杭州云枢智能科技有限公司'
    assert len(company['jobs']) == 2
    assert company['careers'] == {
        'site': '', 'careers_url': None, 'jobs': [], 'error': None
    }


def test_company_report_uses_resolver_and_probe(monkeypatch):
    seen = {}

    def fake_probe(site_url, timeout=8, fetcher=None):
        seen['site'] = site_url
        return {
            'site': site_url,
            'careers_url': site_url.rstrip('/') + '/careers',
            'jobs': ['AI 应用开发工程师'],
            'error': None,
        }

    monkeypatch.setattr(company_hunt, 'probe_careers', fake_probe)
    browser = FakeBrowser([COMPANY_HTML, JOB_HTML])

    report = company_hunt.company_report(
        limit=1,
        browser=browser,
        probe_site=True,
        resolver={'杭州云枢智能科技有限公司': 'www.yunsu-ai.com'},
    )

    assert seen['site'] == 'https://www.yunsu-ai.com'
    careers = report['companies'][0]['careers']
    assert careers['careers_url'] == 'https://www.yunsu-ai.com/careers'
    assert careers['jobs'] == ['AI 应用开发工程师']


def test_cli_parse_file_writes_json(tmp_path, capsys):
    sample = tmp_path / 'sample.html'
    sample.write_text(COMPANY_HTML, encoding='utf-8')
    out = tmp_path / 'nested' / 'parsed.json'

    code = company_hunt.main(['--parse-file', str(sample), '--out', str(out)])

    assert code == 0
    payload = json.loads(out.read_text(encoding='utf-8'))
    assert len(payload) == 3
    assert payload[0]['name'] == '杭州云枢智能科技有限公司'
    assert '离线解析完成' in capsys.readouterr().out


def test_cli_without_live_or_parse_file_returns_2(tmp_path, capsys):
    out = tmp_path / 'should-not-exist.json'

    code = company_hunt.main(['--limit', '1', '--out', str(out)])

    assert code == 2
    assert not out.exists()
    assert '--parse-file' in capsys.readouterr().err


# -------------------------------------------------------------- careers_probe


@pytest.mark.parametrize(
    ('anchor', 'expected'),
    [
        ('<a href="/join">加入我们</a>', 'https://acme.example/join'),
        ('<a href="/careers/">Careers</a>', 'https://acme.example/careers/'),
        ('<a href="/jobs">Jobs</a>', 'https://acme.example/jobs'),
        ('<a href="/join-us">Join Us</a>', 'https://acme.example/join-us'),
        ('<a href="/team/careers">团队</a>', 'https://acme.example/team/careers'),
    ],
)
def test_pick_careers_link_variants(anchor, expected):
    assert careers_probe.pick_careers_link(anchor, 'https://acme.example/') == expected


def test_pick_careers_link_returns_none_when_absent():
    html = '<nav><a href="/">首页</a><a href="/about">关于我们</a></nav>'
    assert careers_probe.pick_careers_link(html, 'https://acme.example/') is None
    assert careers_probe.pick_careers_link('', 'https://acme.example/') is None


def test_extract_job_titles_filters_nav_and_dedupes():
    html = """
    <nav>
      <a href="/">首页</a>
      <a href="/about">关于我们</a>
      <a href="/tech">技术支持</a>
      <a href="/news">查看更多</a>
    </nav>
    <ul class="jobs">
      <li><a href="/jobs/1">AI Agent 工程师</a></li>
      <li><a href="/jobs/2">Python 后端开发工程师</a></li>
      <li><a href="/jobs/2">Python 后端开发工程师</a></li>
      <li><a href="/jobs/3">Java</a></li>
    </ul>
    <h3>算法工程师（杭州）</h3>
    <h4>产品经理</h4>
    """

    titles = careers_probe.extract_job_titles(html)

    assert titles == ['AI Agent 工程师', 'Python 后端开发工程师', '算法工程师（杭州）']
    assert '技术支持' not in titles
    assert '产品经理' not in titles


def test_extract_job_titles_caps_at_20():
    html = ''.join(
        f'<a href="/jobs/{index}">AI研发工程师{index:02d}</a>' for index in range(25)
    )

    titles = careers_probe.extract_job_titles(html)

    assert len(titles) == 20
    assert titles[0] == 'AI研发工程师00'


def test_probe_careers_success_with_injected_fetcher():
    pages = {
        'https://acme.example/': '<nav><a href="/careers">人才招聘</a></nav>',
        'https://acme.example/careers': (
            '<h3>AI 应用开发工程师</h3>'
            '<a href="/job/2">Java 后端开发工程师</a>'
            '<a href="/job/3">产品经理</a>'
        ),
    }
    calls = []

    def fetcher(url):
        calls.append(url)
        return pages[url]

    result = careers_probe.probe_careers('https://acme.example/', fetcher=fetcher)

    assert result == {
        'site': 'https://acme.example/',
        'careers_url': 'https://acme.example/careers',
        'jobs': ['Java 后端开发工程师', 'AI 应用开发工程师'],
        'error': None,
    }
    assert calls == ['https://acme.example/', 'https://acme.example/careers']


def test_probe_careers_fetcher_exception_returns_error():
    def fetcher(url):
        raise RuntimeError('模拟网络故障')

    result = careers_probe.probe_careers('https://acme.example/', fetcher=fetcher)

    assert result['careers_url'] is None
    assert result['jobs'] == []
    assert '模拟网络故障' in result['error']


def test_probe_careers_missing_link_returns_error():
    home = '<nav><a href="/about">关于我们</a></nav>'

    result = careers_probe.probe_careers(
        'https://acme.example/', fetcher=lambda url: home
    )

    assert result['careers_url'] is None
    assert result['error'] == '首页未找到招聘入口'
