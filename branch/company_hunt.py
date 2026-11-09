"""公司找人：先发现杭州中小企业，再反向看它们在 BOSS 在招什么。

与主链路的关系：
- 不复用 engine.py 的筛选/打分，也不写 data/job_pilot.sqlite3；
- 只通过 Duck Typing 使用 BossBrowser 的 _new_page / _goto / _check / _sweep；
- 只做发现与汇报，不发消息、不投递、不点「立即沟通」。

HTML 全部用 re 解析。BOSS 页面结构随时会变，解析不到时字段留空字符串，
绝不根据公司名或其它线索编造行业、规模、融资、岗位。
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from branch.careers_probe import probe_careers

BASE_URL = 'https://www.zhipin.com'
SEARCH_URL = (
    'https://www.zhipin.com/web/geek/company'
    '?city=101210100&scale=303,304&page={page}'
)
MAX_PAGES = 50

CARD_SPLIT_RE = re.compile(
    r'(?=<(?:li|div|article)\b[^>]*class\s*=\s*["\'][^"\']*'
    r'(?:company-card|company-item|company-list-item)[^"\']*["\'])',
    re.I,
)
JOB_CARD_SPLIT_RE = re.compile(
    r'(?=<li\b[^>]*class\s*=\s*["\'][^"\']*'
    r'(?:job-card|job-item|job-list-item)[^"\']*["\'])',
    re.I,
)
GONGSI_ANCHOR_RE = re.compile(
    r'<a\b[^>]*href\s*=\s*["\']([^"\']*?/gongsi/[^"\']+?\.html[^"\']*)["\']'
    r'[^>]*>(.*?)</a\s*>',
    re.I | re.S,
)
HREF_GONGSI_RE = re.compile(
    r'href\s*=\s*["\']([^"\']*?/gongsi/[^"\']+?\.html[^"\']*)["\']', re.I
)
JOB_ANCHOR_RE = re.compile(
    r'<a\b[^>]*href\s*=\s*["\']([^"\']*?/job_detail/[^"\']+?)["\']'
    r'[^>]*>(.*?)</a\s*>',
    re.I | re.S,
)
TAG_RE = re.compile(r'<[^>]+>')

SIZE_RE = re.compile(
    r'(?:\d{1,5}\s*[-~—至]\s*\d{1,5}\s*人'
    r'|\d{1,5}\s*人以上'
    r'|少于\s*\d{1,5}\s*人'
    r'|\d{1,5}\s*人以下)'
)
FUNDING_RE = re.compile(
    r'(未融资|不需要融资|天使轮|(?<![A-Za-z])[A-F]\+?轮'
    r'|战略融资|股权融资|已上市|新三板|IPO)',
    re.I,
)
INDUSTRY_NOISE = frozenset({
    '热招', '急聘', '直招', '五险一金', '年终奖', '双休', '免费班车', '股票期权',
    '定期体检', '弹性工作', '节日福利', '带薪年假', '零食下午茶', '团建聚餐',
    '包吃', '包住', '周末双休', '绩效奖金',
})
NAME_NOISE = frozenset({
    '查看详情', '公司详情', '查看公司', '进入公司', '进入主页', '查看更多',
    '了解更多', '点击查看', '展开', '详情',
})

SALARY_RE = re.compile(
    r'\d{1,3}(?:\.\d+)?\s*[-~—]\s*\d{1,3}(?:\.\d+)?\s*[Kk千万]'
    r'(?:\s*[·*×]\s*\d{1,2}\s*薪)?'
    r'|面议'
    r'|\d{1,4}\s*元\s*/\s*[天时月]'
)
CITY_DOT_RE = re.compile(
    r'([\u4e00-\u9fa5]{2,8})\s*[·・]\s*[\u4e00-\u9fa5]{1,10}'
)

NAME_PATTERNS = (
    r'<(?:h[1-6]|div|span|p|a)\b[^>]*class\s*=\s*["\'][^"\']*'
    r'(?:company-name|company-title|companyName)[^"\']*["\'][^>]*>'
    r'(.*?)</(?:h[1-6]|div|span|p|a)\s*>',
    r'<h[34]\b[^>]*>(.*?)</h[34]\s*>',
)
JOB_TITLE_PATTERNS = (
    r'<[a-z0-9]+\b[^>]*class\s*=\s*["\'][^"\']*'
    r'(?:job-name|job-title|jobName|position-name)[^"\']*["\'][^>]*>'
    r'(.*?)</[a-z0-9]+\s*>',
    r'<h[34]\b[^>]*>(.*?)</h[34]\s*>',
)
SALARY_CLASS_PATTERN = (
    r'<[a-z0-9]+\b[^>]*class\s*=\s*["\'][^"\']*'
    r'(?:salary|job-salary|jobSalary)[^"\']*["\'][^>]*>(.*?)</[a-z0-9]+\s*>'
)
CITY_CLASS_PATTERN = (
    r'<[a-z0-9]+\b[^>]*class\s*=\s*["\'][^"\']*'
    r'(?:job-area|job-city|jobArea|company-area)[^"\']*["\'][^>]*>'
    r'(.*?)</[a-z0-9]+\s*>'
)


def _clean_text(value: str) -> str:
    """去标签、反转义、压平空白。"""
    text = html_lib.unescape(value or '')
    text = re.sub(r'<(?:script|style)\b.*?</(?:script|style)\s*>', ' ', text,
                  flags=re.I | re.S)
    text = TAG_RE.sub(' ', text)
    text = text.replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', text).strip()


def _first_text(pattern: str, block: str) -> str:
    match = re.search(pattern, block, re.I | re.S)
    return _clean_text(match.group(1)) if match else ''


def _canonical_url(href: str) -> str:
    """补全为绝对 URL，并去掉 BOSS 的 ka/lid 之类追踪参数。"""
    href = html_lib.unescape(href or '').strip()
    if not href:
        return ''
    absolute = urljoin(BASE_URL, href)
    parts = urlsplit(absolute)
    if parts.scheme not in ('http', 'https') or not parts.netloc:
        return ''
    return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))


def _card_blocks(html: str) -> list[str]:
    parts = CARD_SPLIT_RE.split(html)
    blocks = [part for part in parts if HREF_GONGSI_RE.search(part)]
    if blocks:
        return blocks
    return [match.group(0) for match in GONGSI_ANCHOR_RE.finditer(html)]


def _job_blocks(html: str) -> list[str]:
    parts = JOB_CARD_SPLIT_RE.split(html)
    blocks = [part for part in parts if '/job_detail/' in part]
    if blocks:
        return blocks

    blocks = []
    for match in re.finditer(r'<li\b[^>]*>(.*?)</li\s*>', html, re.I | re.S):
        if '/job_detail/' in match.group(1):
            blocks.append(match.group(0))
    if blocks:
        return blocks
    return [match.group(0) for match in JOB_ANCHOR_RE.finditer(html)]


def _gongsi_anchor_title(block: str) -> str:
    for match in re.finditer(r'<a\b([^>]*)>', block, re.I):
        attrs = match.group(1)
        if '/gongsi/' not in attrs:
            continue
        title = re.search(r'title\s*=\s*(["\'])(.*?)\1', attrs, re.S)
        if title:
            value = _clean_text(title.group(2))
            if value:
                return value
    return ''


def _extract_name(block: str) -> str:
    for pattern in NAME_PATTERNS:
        name = _first_text(pattern, block)
        if name:
            return name

    title = _gongsi_anchor_title(block)
    if title:
        return title

    # 兜底：公司链接本身就是公司名（且不含规模/融资标签）时才采用。
    match = GONGSI_ANCHOR_RE.search(block)
    if match:
        text = _clean_text(match.group(2))
        if (2 <= len(text) <= 40 and text not in NAME_NOISE
                and not SIZE_RE.search(text) and not FUNDING_RE.search(text)):
            return text
    return ''


def _tag_texts(block: str) -> list[str]:
    texts: list[str] = []
    # 只在 company-tags / tags 容器内取 <li>，避免把外层 company-card 的
    # <li> 当成标签（非贪婪会一路吃到第一个内层 </li>）。
    scopes = re.findall(
        r'<ul\b[^>]*class\s*=\s*["\'][^"\']*(?:company-tags|tags)[^"\']*["\']'
        r'[^>]*>(.*?)</ul\s*>',
        block, re.I | re.S,
    )
    for scope in scopes:
        for match in re.finditer(r'<li\b[^>]*>(.*?)</li\s*>', scope, re.I | re.S):
            texts.append(_clean_text(match.group(1)))
    if not texts:
        for match in re.finditer(r'<li\b[^>]*>(.*?)</li\s*>', block, re.I | re.S):
            inner = match.group(1)
            if re.search(r'<li\b|<ul\b', inner, re.I):
                continue
            texts.append(_clean_text(inner))
    for match in re.finditer(
        r'<(?:span|em)\b[^>]*class\s*=\s*["\'][^"\']*'
        r'(?:tag|label)[^"\']*["\'][^>]*>(.*?)</(?:span|em)\s*>',
        block, re.I | re.S,
    ):
        texts.append(_clean_text(match.group(1)))
    return [text for text in texts if text]


def _class_text(block: str, class_words: tuple[str, ...]) -> str:
    pattern = (
        r'<[a-z0-9]+\b[^>]*class\s*=\s*["\'][^"\']*(?:'
        + '|'.join(class_words)
        + r')[^"\']*["\'][^>]*>(.*?)</[a-z0-9]+\s*>'
    )
    return _first_text(pattern, block)


def _normalize_size(text: str) -> str:
    match = SIZE_RE.search(text or '')
    return re.sub(r'\s+', '', match.group(0)) if match else ''


def _normalize_funding(text: str) -> str:
    match = FUNDING_RE.search(text or '')
    if not match:
        return ''
    value = match.group(1)
    return re.sub(r'^[a-f]', lambda ch: ch.group(0).upper(), value, flags=re.I)


def _normalize_city(text: str) -> str:
    value = _clean_text(text)
    for dot in ('·', '・'):
        if dot in value:
            return value.split(dot, 1)[0].strip()
    return value


def parse_company_cards(html: str) -> list[dict]:
    """解析 BOSS 公司搜索结果卡片。

    返回 [{name, industry, size, funding, url}]，缺字段为空字符串。
    按公司名（没有名字时用 URL）去重，保持页面顺序。
    """
    if not html:
        return []

    cards: list[dict] = []
    seen: set[str] = set()
    for block in _card_blocks(html):
        url_match = HREF_GONGSI_RE.search(block)
        url = _canonical_url(url_match.group(1)) if url_match else ''
        name = _extract_name(block)
        if not name and not url:
            continue
        key = name or url
        if key in seen:
            continue
        seen.add(key)

        tags = _tag_texts(block)
        size = _class_text(block, ('company-size', 'company-scale', 'companyScale'))
        if not size:
            label = re.search(r'(?:规模|人数)\s*[:：]\s*([^<\s，,;；]{2,12})', block)
            size = label.group(1) if label else ''
        if not size:
            size = next((tag for tag in tags if SIZE_RE.search(tag)), '')
        size = _normalize_size(size)

        funding = _class_text(
            block, ('company-financing', 'company-funding', 'financing', 'funding')
        )
        if not funding:
            label = re.search(
                r'(?:融资阶段|融资|轮次)\s*[:：]\s*([^<\s，,;；]{1,12})', block
            )
            funding = label.group(1) if label else ''
        if not funding:
            funding = next((tag for tag in tags if FUNDING_RE.search(tag)), '')
        funding = _normalize_funding(funding)

        industry = _class_text(block, ('company-industry', 'industry'))
        if not industry:
            label = re.search(r'行业\s*[:：]\s*([^<\s，,;；]{1,16})', block)
            industry = label.group(1) if label else ''
        if not industry:
            for tag in tags:
                if SIZE_RE.search(tag) or FUNDING_RE.search(tag):
                    continue
                if tag in INDUSTRY_NOISE or not 2 <= len(tag) <= 16:
                    continue
                industry = tag
                break

        cards.append({
            'name': name,
            'industry': industry,
            'size': size,
            'funding': funding,
            'url': url,
        })
    return cards


def parse_job_cards(html: str) -> list[dict]:
    """解析公司页在招岗位，返回 [{title, salary, city, url}]，缺字段为空字符串。"""
    if not html:
        return []

    jobs: list[dict] = []
    seen: set[tuple] = set()
    for block in _job_blocks(html):
        url_match = JOB_ANCHOR_RE.search(block)
        url = _canonical_url(url_match.group(1)) if url_match else ''

        title = ''
        for pattern in JOB_TITLE_PATTERNS:
            title = _first_text(pattern, block)
            if title:
                break
        if not title and url_match:
            for anchor in re.finditer(r'<a\b([^>]*)>', block, re.I):
                attrs = anchor.group(1)
                if '/job_detail/' not in attrs:
                    continue
                attr = re.search(r'title\s*=\s*(["\'])(.*?)\1', attrs, re.S)
                if attr:
                    value = _clean_text(attr.group(2))
                    if 2 <= len(value) <= 40:
                        title = value
                break
        if not title and url_match and '<' not in url_match.group(2):
            value = _clean_text(url_match.group(2))
            if 2 <= len(value) <= 40:
                title = value

        salary = _clean_text(_first_text(SALARY_CLASS_PATTERN, block))
        if not salary:
            match = SALARY_RE.search(_clean_text(block))
            salary = match.group(0) if match else ''

        city = _normalize_city(_first_text(CITY_CLASS_PATTERN, block))
        if not city:
            match = CITY_DOT_RE.search(_clean_text(block))
            city = match.group(1) if match else ''

        if not title and not url:
            continue
        key = (title, url) if url else (title, salary, city)
        if key in seen:
            continue
        seen.add(key)
        jobs.append({'title': title, 'salary': salary, 'city': city, 'url': url})
    return jobs


def parse_company_site(html: str) -> str:
    """从 BOSS 公司页里找「官网」外链；找不到返回空字符串。"""
    if not html:
        return ''
    for attrs, inner in re.findall(r'<a\b([^>]*)>(.*?)</a\s*>', html, re.I | re.S):
        text = _clean_text(inner)
        if '官网' not in text and '官方网站' not in text:
            continue
        match = re.search(r'href\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if not match:
            continue
        href = html_lib.unescape(match.group(1)).strip()
        if not href or href.lower().startswith(('javascript:', 'mailto:', 'tel:', '#')):
            continue
        absolute = _canonical_url(href)
        if not absolute or 'zhipin.com' in urlsplit(absolute).netloc.lower():
            continue
        return absolute
    return ''


def _close_page(page) -> None:
    try:
        page.close()
    except Exception:
        pass


def _open_html(browser, url: str, timeout: int = 30000) -> str:
    """用 BossBrowser 的鸭子类型接口开页、检查登录/验证、取 body HTML。"""
    page = browser._new_page()
    try:
        browser._goto(page, url, timeout=timeout)
        browser._check(page)
        return page.inner_html('body')
    finally:
        _close_page(page)
        try:
            browser._sweep()
        except Exception:
            pass


def discover_companies(limit: int = 20, browser=None) -> list[dict]:
    """翻 BOSS 公司搜索页，按公司名去重，直到 limit 或无新公司。"""
    if browser is None:
        raise RuntimeError('需要传入 browser（BossBrowser 实例）才能采集')
    if limit <= 0:
        return []

    companies: list[dict] = []
    seen: set[str] = set()
    page_no = 1
    while len(companies) < limit and page_no <= MAX_PAGES:
        html = _open_html(browser, SEARCH_URL.format(page=page_no))
        added = 0
        for card in parse_company_cards(html):
            key = card['name'] or card['url']
            if not key or key in seen:
                continue
            seen.add(key)
            companies.append(card)
            added += 1
            if len(companies) >= limit:
                break
        if added == 0:
            break
        page_no += 1
    return companies


def list_company_jobs(company_url: str, browser) -> list[dict]:
    """打开 BOSS 公司页，解析在招岗位；没有可解析内容时返回空列表。"""
    if not company_url:
        return []
    if browser is None:
        raise RuntimeError('需要传入 browser（BossBrowser 实例）才能采集')
    html = _open_html(browser, company_url)
    return parse_job_cards(html)


def _resolve_site(company: dict, resolver) -> str:
    if resolver is None:
        return ''
    if isinstance(resolver, dict):
        value = resolver.get(company.get('name', ''), '')
    elif callable(resolver):
        try:
            value = resolver(company) or ''
        except Exception:
            value = ''
    else:
        value = ''
    return str(value or '').strip()


def _normalize_site(site: str) -> str:
    site = (site or '').strip()
    if not site:
        return ''
    if not re.match(r'^https?://', site, re.I):
        site = 'https://' + site.lstrip('/')
    return site


def company_report(limit: int = 20, browser=None, probe_site: bool = True,
                   resolver=None) -> dict:
    """串起「发现公司 -> 查在招岗位 -> 探官网招聘页」。

    resolver 可选：dict（公司名 -> 官网）或 callable(company) -> 官网。
    不传时，从 BOSS 公司页里的「官网」外链取；没有官网就跳过探测并写 error。
    """
    generated_at = datetime.now().astimezone().isoformat(timespec='seconds')
    companies = discover_companies(limit=limit, browser=browser)

    rows: list[dict] = []
    for company in companies:
        item = dict(company)
        html = _open_html(browser, item['url']) if item.get('url') else ''
        item['jobs'] = parse_job_cards(html)

        careers = {'site': '', 'careers_url': None, 'jobs': [], 'error': None}
        if probe_site:
            site = _resolve_site(company, resolver) or parse_company_site(html)
            site = _normalize_site(site)
            if site:
                careers = probe_careers(site)
            else:
                careers['error'] = '未找到该公司官网地址'
        item['careers'] = careers
        rows.append(item)

    return {'generated_at': generated_at, 'companies': rows}


def _write_json(path: str, payload) -> Path:
    target = Path(path).expanduser()
    if not target.is_absolute():
        target = Path.cwd() / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    return target


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='python -m branch.company_hunt',
        description='公司找人（实验分支）：发现杭州中小企业并查在招岗位，可选探官网招聘页。'
                    '只做发现与汇报，不投递、不发消息。',
    )
    parser.add_argument('--limit', type=int, default=20, help='最多采集多少家公司（默认 20）')
    parser.add_argument('--out', default=None,
                        help='输出 JSON 路径（默认 data/branch/companies.json）')
    parser.add_argument('--probe-careers', action='store_true',
                        help='额外探测每家公司的官网招聘页')
    parser.add_argument('--parse-file', default=None, metavar='HTML',
                        help='离线解析本地 HTML（不启动浏览器、不联网）')
    parser.add_argument('--live', action='store_true',
                        help='真正启动 BossBrowser 采集（需要已登录的 Chrome）')
    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    if args.parse_file:
        source = Path(args.parse_file)
        try:
            html = source.read_text(encoding='utf-8', errors='replace')
        except OSError as exc:
            print(f'读取失败：{exc}', file=sys.stderr)
            return 1
        cards = parse_company_cards(html)
        out = args.out or 'data/branch/parsed.json'
        target = _write_json(out, cards)
        print(f'离线解析完成：{len(cards)} 家公司 -> {target}')
        for card in cards[:10]:
            print(f"  - {card['name']} | {card['industry']} | "
                  f"{card['size']} | {card['funding']}")
        if len(cards) > 10:
            print(f'  ... 其余 {len(cards) - 10} 家见 JSON')
        return 0

    if not args.live:
        print('离线模式只能使用 --parse-file；真实采集请加 --live。', file=sys.stderr)
        return 2

    from browser_adapter import BossBrowser

    browser = BossBrowser()
    try:
        try:
            report = company_report(
                limit=args.limit, browser=browser, probe_site=args.probe_careers
            )
        except Exception as exc:
            print(f'采集失败：{exc}', file=sys.stderr)
            return 1
    finally:
        try:
            browser.close()
        except Exception:
            pass

    out = args.out or 'data/branch/companies.json'
    target = _write_json(out, report)
    companies = report['companies']
    job_total = sum(len(item['jobs']) for item in companies)
    print(f'采集完成：{len(companies)} 家公司，{job_total} 个在招岗位 -> {target}')
    for item in companies[:10]:
        print(f"  - {item['name']}：{len(item['jobs'])} 个岗位")
    if args.probe_careers:
        hit = sum(1 for item in companies if item['careers'].get('careers_url'))
        print(f'官网招聘页：命中 {hit} 家')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
