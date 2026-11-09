# 公司找人（实验分支）

这是一个**独立实验**：方向与主链路相反。

- 主链路：岗位找人 —— BOSS 搜关键词 → 硬筛 → 打分 → 自动打招呼。
- 本分支：公司找人 —— 先定位公司 → 反查这家公司在 BOSS 在招什么 → 再核验它官网的招聘页。

本分支**只做发现与汇报**：不投递、不发消息、不点「立即沟通」，也不写主数据库。

## 真实页面结论（2026-11 实测）

这些是踩过的坑，后续改解析先看这里：

| 需求 | 实际可用的地址 | 说明 |
|---|---|---|
| 公司列表 | `https://www.zhipin.com/gongsi/` | `/web/geek/company` 会 404；`/gongsi/` 默认就是会话城市（杭州），**没有**规模/关键词参数生效，列出来的是品牌大厂 |
| 公司在招岗位 | `https://www.zhipin.com/gongsi/job/<id>.html` | 公司主页 `/gongsi/<id>.html` 只展示「热招职位」3 条，全部职位要点进 `/gongsi/job/<id>.html`（实测 23 条） |
| 岗位 → 公司 | 岗位详情页里的 `a[href*="/gongsi/xxx.html"]` | 页面导航里的 `/gongsi/` 没有 `.html`，必须要求 `.html` 结尾，否则会把「公司」导航当成公司主页 |

对应实现：

- 品牌列表用 `<div class="sub-li">` 结构：`a.company-info > div.conpany-text > h4`（公司名）+ `span`（融资/行业），`a.about-info`（热招岗位）。
- 职位页用 `a[href*="/job_detail/"]`、`.job-name`、`.job-card-box`；薪资是明文（`25-45K`）。
- 城市在职位页里是自由文本，用 `KNOWN_CITIES` 白名单兜底，避免把招聘者姓名（「李女士」）当城市。
- 列表页**没有公司规模字段**，`size` 一律留空，不猜。

## 与主链路的关系

- 代码全部位于 `branch/`，与 `app.py`、`engine.py`、`browser_adapter.py` 解耦，不修改主程序。
- 唯一耦合是按鸭子类型复用 `BossBrowser`（`_new_page()` / `_goto()` / `_check()` / `_sweep()` / `_call()`）。
- **不要另起一个 Playwright 连同一个 Chrome**：实测并行 attach 会 `connect_over_cdp: Timeout 30000ms`。正确姿势是用主程序暴露的三个只读接口（见下）。
- 输出只写 `data/branch/*.json`，不碰 `data/job_pilot.sqlite3`。
- 测试全部离线：不启动 Chrome/Playwright，不发真实网络请求。

## 怎么跑

### 1. 通过主程序的只读接口（推荐）

主程序在跑时（`python app.py`，默认 `127.0.0.1:8765`），分支借用同一个 Chrome：

```powershell
# 公司列表（品牌大厂，慎用；limit 1-50）
Invoke-RestMethod -Method Post http://127.0.0.1:8765/api/branch/discover `
  -ContentType 'application/json' -Body '{"limit":6}'

# 岗位 → 公司：拿到公司页地址 + 该公司全部在招岗位
Invoke-RestMethod -Method Post http://127.0.0.1:8765/api/branch/company-of-job `
  -ContentType 'application/json' -Body '{"job_url":"https://www.zhipin.com/job_detail/xxx.html"}'

# 指定公司页地址，直接列全部在招岗位
Invoke-RestMethod -Method Post http://127.0.0.1:8765/api/branch/company-jobs `
  -ContentType 'application/json' -Body '{"url":"https://www.zhipin.com/gongsi/xxx.html"}'
```

三个接口都是只读的，且只在托管暂停时调用比较稳妥（它们会占用浏览器工作线程）。

实测（小麦助教）：

```
== 小麦助教 | https://www.zhipin.com/gongsi/99fc776f746341c103N609m9.html | jobs 23
   - 高级全栈开发工程师 | 25-50K | 杭州
   - AI 全栈工程师（AI 应用 / Agent 方向） | 25-45K | 杭州
   - JAVA开发工程师 | 13-25K | 杭州
```

### 2. 离线解析本地 HTML（不需要浏览器、不联网）

```powershell
python -m branch.company_hunt --parse-file data/branch/sample.html --out data/branch/parsed.json
```

### 3. 独立 `--live` 采集（主程序必须停掉）

```powershell
python -m branch.company_hunt --live --limit 20 --out data/branch/companies.json
python -m branch.company_hunt --live --limit 20 --probe-careers --out data/branch/companies.json
```

`--live` 会自己启动 Chrome；主程序在跑时**不要**这么用。不加 `--live` 且不给 `--parse-file` 时退出码为 `2`。

### 4. 测试

```powershell
python -m pytest -q
```

## 输出

- 实时采集：`data/branch/companies.json`
- 离线解析：`data/branch/parsed.json`

```json
{
  "generated_at": "2026-11-09T08:20:00+08:00",
  "companies": [
    {
      "name": "杭州某科技有限公司",
      "industry": "人工智能",
      "size": "",
      "funding": "B轮",
      "url": "https://www.zhipin.com/gongsi/xxxx.html",
      "hot_job": {"title": "AI Agent 工程师", "salary": "25-40K", "url": "..."},
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

`careers` 的约定：`error` 为 `null` 表示探测成功（`jobs` 仍可能为空）；找不到招聘入口写 `首页未找到招聘入口`；没有官网写 `未找到该公司官网地址`；网络异常写入错误文本，不中断整份报告。

## 已知限制

1. **公司列表只有品牌大厂**：`/gongsi/` 不接受关键词/规模筛选参数（实测 query 被忽略），所以「杭州中小企业」目前只能从**已有岗位数据**里反查（岗位 → 公司 → 全部在招），不能靠列表页筛。
2. **规模字段缺失**：列表页不给公司规模，规模仍要靠主链路的岗位详情补全。
3. **BOSS 反爬与登录态**：频繁翻页可能触发验证；`_check()` 会发现并抛错，本分支不绕过。
4. **页面结构随时会变**：解析基于类名约定，改版即可能失效；缺字段一律留空，不编造。
5. **官网结构千变万化**：招聘入口可能叫「加入我们」「人才招聘」「Careers」「Jobs」，也可能是 JS 渲染；`pick_careers_link` 只匹配首页静态 HTML。
6. **只做发现**：不投递、不发消息、不打分。
7. **进度未持久化**：只写 JSON，不做增量/去重历史。

## 下一步（未做）

- 用主数据库里 `company_size` 落在 100–999、且有融资记录的公司在招岗位，做「公司池 → 全部在招岗位」的批量报告。
- 官网地址目前只有 `parse_company_site`（从公司页找「官网」外链），尚未接到批量流程里。
