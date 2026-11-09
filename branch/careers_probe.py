"""官网招聘页探测。

输入一个公司官网首页，找到招聘入口，再粗略抽取在招岗位标题。
只做发现与汇报：不提交表单、不发消息、不访问 BOSS。

设计原则：
- 只用标准库（requests 仅在默认 fetcher 内延迟导入）。
- 页面结构千变万化，所有函数都容忍缺失，解析不到就返回空，绝不编造。
- probe_careers 不向外抛异常，失败写进 error 字段。
"""
from __future__ import annotations

import html as html_lib
import re
from urllib.parse import urljoin

# 中文关键词直接子串匹配；英文关键词用边界，避免 "hr" 命中 "chrome" 之类。
CN_CAREERS_KEYWORDS = ('招聘', '加入我们', '人才招聘')
CAREERS_KEYWORD_RE = re.compile(
    r'(?<![a-z0-9])(?:careers?|jobs?|join[-_ ]?us|hr)(?![a-z0-9])', re.I
)
SKIP_PREFIXES = ('javascript:', 'mailto:', 'tel:', 'data:', '#')

ANCHOR_RE = re.compile(r'<a\b([^>]*)>(.*?)</a\s*>', re.I | re.S)
HREF_RE = re.compile(r'href\s*=\s*(["\'])(.*?)\1', re.I | re.S)
HEADING_RE = re.compile(r'<h([34])\b[^>]*>(.*?)</h\1\s*>', re.I | re.S)
TAG_RE = re.compile(r'<[^>]+>')

# 岗位标题必须命中的关键词（AI / Agent 用英文边界，避免命中 training 里的 ai）。
JOB_KEYWORD_RE = re.compile(
    r'工程师|开发|算法|架构|技术|研发|(?<![A-Za-z])(?:AI|Agent)(?![A-Za-z])', re.I
)

# 导航 / 页脚 / 通用按钮，即使含关键词也不当岗位。
NAV_BLOCKLIST = frozenset({
    '首页', '关于我们', '联系我们', '加入我们', '人才招聘', '招聘', '社会招聘',
    '校园招聘', '新闻动态', '产品中心', '解决方案', '技术支持', '技术文档',
    '技术博客', '技术社区', '服务支持', '隐私政策', '法律声明', '投资者关系',
    '查看更多', '了解更多', '更多职位', '阅读全文', '返回顶部', '上一篇', '下一篇',
})


def _clean_text(value: str) -> str:
    """去掉标签、反转义实体、压平空白。"""
    text = html_lib.unescape(value or '')
    text = TAG_RE.sub(' ', text)
    text = text.replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', text).strip()


def pick_careers_link(html: str, base_url: str) -> str | None:
    """从官网首页 HTML 里挑出招聘入口，返回绝对 URL；找不到返回 None。

    优先锚文本命中（「加入我们」「人才招聘」「Careers」等），其次 href 命中。
    """
    if not html or not base_url:
        return None

    text_hit: str | None = None
    href_hit: str | None = None
    for attrs, inner in ANCHOR_RE.findall(html):
        href_match = HREF_RE.search(attrs)
        if not href_match:
            continue
        href = html_lib.unescape(href_match.group(2)).strip()
        if not href or href.lower().startswith(SKIP_PREFIXES):
            continue

        text = _clean_text(inner)
        text_matches = (
            any(keyword in text for keyword in CN_CAREERS_KEYWORDS)
            or bool(CAREERS_KEYWORD_RE.search(text))
        )
        href_matches = (
            '招聘' in href
            or '加入我们' in href
            or bool(CAREERS_KEYWORD_RE.search(href))
        )
        if not (text_matches or href_matches):
            continue

        absolute = urljoin(base_url, href)
        if text_matches:
            if text_hit is None:
                text_hit = absolute
        elif href_hit is None:
            href_hit = absolute

    return text_hit or href_hit


def extract_job_titles(html: str) -> list[str]:
    """从招聘页粗提岗位标题：<a> 文本或 <h3>/<h4> 文本，4-40 字，去重，最多 20 条。"""
    if not html:
        return []

    candidates: list[str] = []
    for _attrs, inner in ANCHOR_RE.findall(html):
        candidates.append(_clean_text(inner))
    for match in HEADING_RE.finditer(html):
        candidates.append(_clean_text(match.group(2)))

    titles: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        title = raw.strip(' \t\r\n·|/-—–')
        if not title or title in NAV_BLOCKLIST:
            continue
        if not 4 <= len(title) <= 40:
            continue
        if not JOB_KEYWORD_RE.search(title):
            continue
        key = title.casefold()
        if key in seen:
            continue
        seen.add(key)
        titles.append(title)
        if len(titles) >= 20:
            break
    return titles


def _default_fetcher(url: str, timeout: float) -> str:
    import requests

    response = requests.get(
        url, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0'}
    )
    if response.status_code != 200:
        raise RuntimeError(f'HTTP {response.status_code}')
    if not response.encoding or response.encoding.lower() == 'iso-8859-1':
        response.encoding = response.apparent_encoding or 'utf-8'
    return response.text


def _as_text(payload) -> str:
    if payload is None:
        return ''
    if isinstance(payload, bytes):
        return payload.decode('utf-8', errors='replace')
    return str(payload)


def probe_careers(site_url: str, timeout: float = 8, fetcher=None) -> dict:
    """抓官网首页 -> 找招聘链接 -> 抓招聘页 -> 返回岗位标题。

    fetcher(url) -> str 可注入（测试用）。非 200 或任何异常都写进 error，
    本函数保证不抛未捕获异常。
    """
    result = {'site': site_url, 'careers_url': None, 'jobs': [], 'error': None}
    if not site_url or not str(site_url).strip():
        result['error'] = '缺少官网地址'
        return result

    site = str(site_url).strip()
    result['site'] = site
    fetch = fetcher or (lambda url: _default_fetcher(url, timeout))

    try:
        home = _as_text(fetch(site))
    except Exception as exc:  # 网络 / 非 200 / 注入 fetcher 主动抛错
        result['error'] = f'首页抓取失败: {exc}'
        return result

    try:
        link = pick_careers_link(home, site)
    except Exception as exc:
        result['error'] = f'首页解析失败: {exc}'
        return result
    if not link:
        result['error'] = '首页未找到招聘入口'
        return result
    result['careers_url'] = link

    try:
        careers_html = _as_text(fetch(link))
    except Exception as exc:
        result['error'] = f'招聘页抓取失败: {exc}'
        return result

    try:
        result['jobs'] = extract_job_titles(careers_html)
    except Exception as exc:
        result['error'] = f'招聘页解析失败: {exc}'
    return result
