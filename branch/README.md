# 公司找人（实验分支）

这是一个**独立实验**：方向与主链路相反。

- 主链路：岗位找人 —— BOSS 搜关键词 → 硬筛 → 打分 → 自动打招呼。
- 本分支：公司找人 —— 先找杭州的中小企业 → 反查这些公司在 BOSS 在招什么 → 再核验它们官网的招聘页。

本分支**只做发现与汇报**：不投递、不发消息、不点「立即沟通」，也不写主数据库。

## 与主链路的关系

- 代码全部位于 `branch/`，与 `app.py`、`engine.py`、`browser_adapter.py` 解耦。
- 不修改主程序、`public/`、`requirements.txt`、`.gitignore`。
- 唯一的耦合是按鸭子类型复用 `BossBrowser` 的四个方法：`_new_page()`、`_goto()`、`_check()`、`_sweep()`，仅在 `--live` 时导入。
- 输出只写 `data/branch/*.json`，不碰 `data/job_pilot.sqlite3`。
- 测试全部离线：不启动 Chrome/Playwright，不发真实网络请求。

## 目录

```
branch/
  __init__.py        分支说明
  company_hunt.py    公司发现、岗位反查、报告串接、CLI
  careers_probe.py   官网招聘页探测（找入口 + 粗提岗位标题）
data/branch/         离线样例与运行输出（sample.html 仅本地测试用）
tests/test_branch.py 离线 pytest
```

## 怎么跑

在项目根目录执行。

### 1. 离线解析本地 HTML（不需要浏览器、不联网）

```powershell
python -m branch.company_hunt --parse-file data/branch/sample.html --out data/branch/parsed.json
```

适合调选择器、验证解析逻辑。`--parse-file` 模式只解析公司卡片，不查岗位、不探官网。

### 2. 采集公司 + 在招岗位

```powershell
python -m branch.company_hunt --live --limit 20 --out data/branch/companies.json
```

真实采集**必须加 `--live`**，程序才会启动 `BossBrowser`。不加 `--live` 且不给 `--parse-file` 时，程序会打印提示并以退出码 `2` 结束，避免误触发浏览器。

### 3. 额外探测官网招聘页

```powershell
python -m branch.company_hunt --live --limit 20 --probe-careers --out data/branch/companies.json
```

### 4. 测试

```powershell
python -m pytest -q
```

## 输出

默认输出：

- 实时采集：`data/branch/companies.json`
- 离线解析：`data/branch/parsed.json`

目录不存在会自动创建，JSON 为 UTF-8、`ensure_ascii=False`、`indent=2`。

实时报告结构：

```json
{
  "generated_at": "2026-11-09T08:20:00+08:00",
  "companies": [
    {
      "name": "杭州某科技有限公司",
      "industry": "人工智能",
      "size": "100-499人",
      "funding": "B轮",
      "url": "https://www.zhipin.com/gongsi/xxxx.html",
      "jobs": [
        {"title": "AI Agent 工程师", "salary": "25-40K·14薪", "city": "杭州", "url": "..."}
      ],
      "careers": {
        "site": "https://www.example.com",
        "careers_url": "https://www.example.com/careers",
        "jobs": ["AI 应用开发工程师"],
        "error": null
      }
    }
  ]
}
```

`careers` 的约定：

- `error` 为 `null` 表示探测成功（即使没提到岗位标题，`jobs` 也可能为空）。
- 首页找不到招聘入口：`error` 为 `首页未找到招聘入口`。
- 公司没有官网：`error` 为 `未找到该公司官网地址`。
- 网络/HTTP 异常：错误文本写入 `error`，不会中断整份报告。

## 已知限制

1. **BOSS 反爬与登录态**：公司搜索页需要有效登录态，频繁翻页可能触发验证码/滑块/风控。`BossBrowser` 的 `_check()` 负责发现异常，但本分支不做绕过；被拦时通常只能拿到空列表或旧页面。
2. **页面结构随时会变**：解析全部基于正则和类名约定（`company-card`、`company-name`、`job-card`、`job-name` 等），BOSS 改版后可能整体失效。缺字段一律留空，不猜测、不编造。
3. **官网结构千变万化**：招聘入口可能叫「加入我们」「人才招聘」「Careers」「Jobs」，也可能在页脚、二级域名或 JS 渲染后才出现。`pick_careers_link` 只做首页静态 HTML 的关键词匹配，找不到就返回 `None`；`extract_job_titles` 只是粗提，会把部分非岗位链接漏掉或误收。
4. **只做发现**：不投递、不发消息、不点「立即沟通」；不做候选人匹配打分。
5. **城市/规模筛选依赖 URL 参数**：`city=101210100`（杭州）、`scale=303,304`（100-499 / 500-999 人）。参数含义随 BOSS 调整可能变化。
6. **官网探测是同步串行请求**：公司多时较慢；默认超时 8 秒，失败只记录错误。
7. **数据仅本地 JSON**：不做持久化、去重历史、增量更新。

## 真实页面上还需要人工确认的选择器

- 公司卡片容器是否仍为 `company-card` / `company-item` / `company-list-item`。
- 公司名是否仍在 `.company-name`，还是改成 `h3` 内的其他节点。
- 规模/融资是否仍在 `company-tags` 的 `<li>` 里，以及「100-499人」的文案格式。
- 公司详情页的「官网」外链是否仍带 `官网` 文本或 `target=_blank`。
- 岗位卡片是否仍为 `.job-card`，薪资/城市类名是否变化。
- 招聘入口是否改为 JS 渲染、需要滚动或点击后才出现。
