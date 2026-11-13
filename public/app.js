(() => {
  'use strict';
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const state = { data: null, jobs: [], selected: null, filter: 'all', jobQuery: '', jobPage: 1, pageSize: 20, busy: false };
  const els = {
    app: $('#app'), stats: $('#statsGrid'), jobs: $('#jobList'), detail: $('#jobDetail'), jobCount: $('#jobCount'), logs: $('#logList'),
    toast: $('#toast'), resume: $('#resumeText'), resumeMeta: $('#resumeMeta'), mode: $('#modeSelect'), minScore: $('#minScore'), dailyLimit: $('#dailyLimit'), interval: $('#intervalSeconds'), enabled: $('#enabledToggle'), autoApprove: $('#autoApproveToggle'), autoCollect: $('#autoCollectToggle'), modeChip: $('#modeChip'),
    title: $('#automationTitle'), autoText: $('#automationText'), banner: $('#statusBanner'), connection: $('#connection'), pause: $('#pauseBtn'),
    search: $('#jobSearch'), pager: $('#jobPager'), pageSize: $('#pageSize')
  };
  const rulesEls = { titles: $('#ruleTitles'), cities: $('#ruleCities'), districts: $('#ruleDistricts'), minSalary: $('#ruleMinSalary'), maxSalary: $('#ruleMaxSalary'), skills: $('#ruleSkills'), blacklist: $('#ruleBlacklist'), companyMin: $('#ruleCompanyMin'), companyMax: $('#ruleCompanyMax'), recruitment: $('#ruleRecruitment'), education: $('#ruleEducation'), greeting: $('#ruleGreeting') };
  function csvList(value) { return Array.isArray(value) ? value.join(', ') : safe(value); }
  function renderRules(rules) { const r = rules || {}; rulesEls.titles.value = csvList(r.titles); rulesEls.cities.value = csvList(r.cities); rulesEls.districts.value = csvList(r.districts); rulesEls.minSalary.value = first(r, ['min_salary'], ''); rulesEls.maxSalary.value = first(r, ['max_salary'], ''); rulesEls.skills.value = csvList(r.skills); rulesEls.blacklist.value = csvList(r.blacklist); rulesEls.companyMin.value = first(r, ['company_min'], ''); rulesEls.companyMax.value = first(r, ['company_max'], ''); rulesEls.recruitment.value = r.recruitment_type || ''; rulesEls.education.value = r.max_education || ''; rulesEls.greeting.value = r.greeting || ''; }
  function ruleList(value) { return safe(value).split(/[,，\n]/).map(x => x.trim()).filter(Boolean); }
  const safe = (value, fallback = '') => value === null || value === undefined ? fallback : String(value);
  const first = (obj, keys, fallback = '') => { for (const key of keys) if (obj && obj[key] !== undefined && obj[key] !== null) return obj[key]; return fallback; };
  const asArray = value => Array.isArray(value) ? value : [];
  const num = (value, fallback = 0) => { const n = Number(value); return Number.isFinite(n) ? n : fallback; };
  const timeLabel = value => { if (!value) return '—'; const d = new Date(value); return Number.isNaN(d.getTime()) ? safe(value).slice(0, 8) : d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }); };
  function toast(message, error = false) { els.toast.textContent = message; els.toast.className = `toast show${error ? ' error' : ''}`; window.clearTimeout(toast.timer); toast.timer = window.setTimeout(() => els.toast.classList.remove('show'), 3200); }
  async function api(path, options = {}) {
    const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
    let body = null; try { body = await response.json(); } catch (_) { body = {}; }
    if (!response.ok) throw new Error(safe(body.error || body.message, `请求失败（${response.status}）`));
    return body;
  }
  function normalizeJob(raw, index) {
    raw = raw || {};
    return {
      id: safe(first(raw, ['id', 'job_id', 'jobId'], `job-${index}`)),
      title: safe(first(raw, ['title', 'name', 'position'], '未命名岗位')),
      company: safe(first(raw, ['company', 'company_name', 'companyName'], '未提供公司')),
      city: safe(first(raw, ['city', 'location', 'address'], '杭州')),
      salary: safe(first(raw, ['salary', 'salary_range', 'salaryRange'], '')).trim() || '薪资待确认',
      score: first(raw, ['score', 'match_score', 'matchScore', 'ai_score'], null),
      reason: safe(first(raw, ['reason', 'score_reason', 'analysis_reason'], '')),
      analysisSource: safe(first(raw, ['analysis_source', 'analysisSource'], '')),
      analyzed: Boolean(first(raw, ['analyzed', 'analysis_done', 'analysisDone'], false)) || first(raw, ['score', 'match_score', 'matchScore', 'ai_score'], null) !== null || Boolean(first(raw, ['reason', 'score_reason'], '')),
      approved: Boolean(first(raw, ['approved'], false)),
      attempt: first(raw, ['attempt', 'attempts'], null),
      status: safe(first(raw, ['status', 'state'], 'pending')).toLowerCase(),
      description: safe(first(raw, ['description', 'desc', 'detail', 'content'], '暂无岗位描述。')),
      tags: asArray(first(raw, ['tags', 'labels'], [])).map(safe),
      greeting: safe(first(raw, ['greeting', 'platform_greeting', 'contact_message'], '')),
      source: safe(first(raw, ['source', 'platform'], 'BOSS')),
      raw
    };
  }
  function normalizeState(payload) {
    const data = payload && payload.data && typeof payload.data === 'object' ? payload.data : (payload || {});
    const jobs = asArray(data.jobs || data.opportunities).map(normalizeJob);
    return { ...data, jobs, profile: data.profile || {}, rules: data.rules || {}, automation: data.automation || {}, stats: data.stats || {}, logs: asArray(data.logs || data.log) };
  }
  function make(tag, text, className) { const el = document.createElement(tag); if (className) el.className = className; if (text !== undefined) el.textContent = safe(text); return el; }
  function renderStats(data) {
    const s = data.stats || {}; const values = [
      ['待处理岗位', first(s, ['pending', 'pending_jobs', 'new_jobs'], data.jobs.filter(j => ['pending', 'new'].includes(j.status)).length), '条'],
      ['已筛选', first(s, ['shortlisted', 'shortlisted_jobs'], data.jobs.filter(j => ['shortlisted', 'approved'].includes(j.status)).length), '条'],
      ['已沟通', first(s, ['contacted', 'communicated', 'sent'], data.jobs.filter(j => ['contacted', 'communicated'].includes(j.status)).length), '次'],
      ['今日额度', first(s, ['today_remaining', 'remaining', 'quota_remaining'], '—'), '次剩余']
    ];
    els.stats.replaceChildren(...values.map(([label, value, note]) => { const card = make('div', undefined, 'stat'); card.append(make('span', label, 'stat-label'), make('div', value, 'stat-value'), make('span', note, 'stat-note')); return card; }));
  }
  function matchesQuery(job) {
    const q = state.jobQuery.trim().toLowerCase();
    if (!q) return true;
    return [job.title, job.company, job.city, job.salary, statusLabel(job.status), job.raw && job.raw.experience]
      .map(x => safe(x).toLowerCase()).join(' ').includes(q);
  }
  function filteredJobs() { return state.jobs.filter(j => (state.filter === 'all' || (state.filter === 'shortlisted' ? ['shortlisted', 'approved'].includes(j.status) : ['pending', 'new', ''].includes(j.status))) && matchesQuery(j)); }
  function renderPager(total, pages) {
    els.pager.replaceChildren();
    if (!total) { els.pager.style.display = 'none'; return; }
    els.pager.style.display = 'flex';
    const prev = make('button', '‹ 上一页', 'pager-btn'); prev.type = 'button'; prev.disabled = state.jobPage <= 1;
    const next = make('button', '下一页 ›', 'pager-btn'); next.type = 'button'; next.disabled = state.jobPage >= pages;
    const info = make('span', `共 ${total} 条 · 第 ${state.jobPage} / ${pages} 页`, 'pager-info');
    prev.addEventListener('click', () => { state.jobPage = Math.max(1, state.jobPage - 1); renderJobs(); });
    next.addEventListener('click', () => { state.jobPage = Math.min(pages, state.jobPage + 1); renderJobs(); });
    els.pager.append(prev, info, next);
  }
  function renderJobs() {
    const jobs = filteredJobs();
    const pages = Math.max(1, Math.ceil(jobs.length / state.pageSize));
    state.jobPage = Math.min(Math.max(1, state.jobPage), pages);
    const start = (state.jobPage - 1) * state.pageSize;
    const visible = jobs.slice(start, start + state.pageSize);
    els.jobCount.textContent = String(state.jobs.length); els.jobs.replaceChildren();
    if (!jobs.length) { const empty = make('div', undefined, 'empty-state'); empty.append(make('div', '◎', 'empty-icon'), make('strong', state.jobs.length ? '没有符合条件的岗位' : '岗位还没到达这里'), make('p', state.jobs.length ? '换一个筛选条件或关键词试试。' : '导入岗位数据，或连接 BOSS 采集杭州岗位，开始建立你的机会清单。')); els.jobs.append(empty); renderPager(0, 0); return; }
    for (const job of visible) { const row = make('article', undefined, `job-row${state.selected && state.selected.id === job.id ? ' selected' : ''}`); row.dataset.id = job.id; const logo = make('div', (job.company || '?').slice(0, 1), 'job-logo'); const middle = make('div'); middle.append(make('div', job.title, 'job-title'), make('div', job.company, 'job-company')); const meta = make('div', undefined, 'job-meta'); meta.append(make('div', job.score === null ? '待分析' : num(job.score) < 0 ? '硬筛拒绝' : `${Math.round(num(job.score))} / 100`, 'job-score'), make('div', `${job.city} · ${job.salary}`, 'job-city'), make('div', statusLabel(job.status), 'job-tag')); row.append(logo, middle, meta); row.addEventListener('click', () => selectJob(job.id)); els.jobs.append(row); }
    renderPager(jobs.length, pages);
  }
  function statusLabel(status) { return ({ contacted: '已沟通', communicated: '已沟通', sent: '已沟通', approved: '审核入队', matched: '已匹配', simulated: '模拟完成', blocked: '已阻断', uncertain: '待确认', rejected: '硬筛拒绝', shortlisted: '已筛选', pending: '待处理', new: '新岗位' })[status] || (status ? status : '待处理'); }
  function renderDetail() {
    els.detail.replaceChildren(); const job = state.selected;
    if (!job) { els.detail.append(make('div', undefined, 'empty-state')); const box = els.detail.firstChild; box.append(make('div', '✦', 'empty-icon'), make('strong', '从清单选择一个岗位'), make('p', '这里会显示岗位描述、AI 评分与沟通动作。')); $('#detailLabel').textContent = '未选择'; return; }
    $('#detailLabel').textContent = statusLabel(job.status); const kicker = make('span', 'OPPORTUNITY / ' + job.source.toUpperCase(), 'detail-kicker'); const title = make('h3', job.title, 'detail-title'); const company = make('div', job.company, 'detail-company'); const line = make('div', undefined, 'detail-line'); [job.city, job.salary, `规模：${job.raw.company_size || '待核验'}`, `学历：${job.raw.education || '待核验'}`, `经验：${job.raw.experience || '待核验'}`, `招聘：${({ social: '社招', campus: '校招', internship: '实习' })[job.raw.recruitment_type] || job.raw.recruitment_type || '待核验'}`, job.score === null ? '待分析' : num(job.score) < 0 ? '硬筛拒绝' : `${job.analysisSource === 'local' || job.analysisSource === 'local_fallback' ? '本地规则' : 'AI 匹配'} ${Math.round(num(job.score))}`].forEach(x => line.append(make('span', x))); const copy = make('p', [job.reason ? '分析依据：' + job.reason : '', job.description].filter(Boolean).join('\n\n'), 'detail-copy'); const risks = asArray(first(job.raw, ['risks'], [])).map(safe); const missing = asArray(first(job.raw, ['missing_skills', 'missingSkills'], [])).map(safe); const riskNote = make('p', `风险：${risks.length ? risks.join('、') : '未提供'}｜缺失技能：${missing.length ? missing.join('、') : '未提供'}`, 'detail-copy'); const draftValue = first(job.raw, ['draft', 'ai_draft'], ''); const draftText = typeof draftValue === 'object' ? safe(first(draftValue, ['text', 'content'], '')) : safe(draftValue); const draft = make('textarea', draftText, 'draft-box'); draft.placeholder = 'AI 草稿会在分析后出现在这里，仅供复制使用。'; draft.readOnly = true; const draftCopy = make('button', '复制草稿', 'outline-button'); draftCopy.disabled = !draftText; draftCopy.addEventListener('click', async () => { try { await navigator.clipboard.writeText(draftText); toast('草稿已复制'); } catch (_) { draft.focus(); draft.select(); toast('请手动复制草稿'); } }); const actions = make('div', undefined, 'detail-actions'); const analyze = make('button', 'AI 分析', 'outline-button'); analyze.addEventListener('click', () => runAction(`/api/analyze`, { id: job.id }, '分析完成')); const terminal = ['sent', 'contacted', 'communicated', 'blocked', 'uncertain', 'pending', 'rejected', 'simulated']; const approveAllowed = job.analyzed && !terminal.includes(job.status); const approveLabel = ['sent', 'contacted', 'communicated'].includes(job.status) ? '已沟通' : job.status === 'rejected' || num(job.score) < 0 ? '硬筛拒绝' : approveAllowed ? '审核入队' : '不可审核'; const approve = make('button', approveLabel, 'primary-button'); approve.disabled = !approveAllowed; if (!approveAllowed) approve.title = '该岗位处于终态或尚未分析'; approve.addEventListener('click', () => approveJob(job)); actions.append(analyze, draftCopy, approve); const note = make('p', 'AI 草稿供复制使用；BOSS 使用平台招呼语。真实模式会发起 BOSS 沟通，遇到登录或验证会明确停在待处理。', 'detail-copy'); els.detail.append(kicker, title, company, line, copy, riskNote, draft, actions, note);
  }
  async function approveJob(job) { await runAction(`/api/jobs/${encodeURIComponent(job.id)}/approve`, {}, '已加入审核队列'); }
  async function runAction(path, body, success) { if (state.busy) return; setBusy(true); try { const result = await api(path, { method: 'POST', body: JSON.stringify(body || {}) }); if (path === '/api/profile') state.formDirty = false; toast(result.message || (path === '/api/browser/collect' ? `采集完成：${asArray(result.jobs).length} 个岗位` : success)); await load(); } catch (e) { toast(e.message, true); } finally { setBusy(false); } }
  function renderResume(profile) { const text = safe(first(profile, ['resume_text', 'resumeText', 'text'], '')); if (document.activeElement !== els.resume) els.resume.value = text; els.resumeMeta.textContent = text ? `${text.length} 字符 · 已从后端加载` : '尚未加载档案'; }
  function renderAutomation(a, rules) { const x = { ...rules, ...a }; els.mode.value = first(x, ['mode'], 'dry_run'); els.modeChip.textContent = els.mode.value === 'live' ? 'LIVE / BOSS' : 'DRY RUN'; els.minScore.value = num(first(x, ['min_score', 'minScore'], 70), 70); els.dailyLimit.value = num(first(x, ['daily_limit', 'dailyLimit'], 10), 10); els.interval.value = num(first(x, ['interval_seconds', 'intervalSeconds'], 90), 90); els.enabled.checked = Boolean(first(x, ['enabled'], false)); els.autoApprove.checked = Boolean(first(x, ['auto_approve', 'autoApprove'], false)); els.autoCollect.checked = Boolean(first(x, ['auto_collect', 'autoCollect'], false)); const live = els.mode.value === 'live'; els.title.textContent = els.enabled.checked ? (live ? '真实托管已启用' : '模拟托管已启用') : '托管尚未启动'; els.autoText.textContent = els.enabled.checked ? (live ? '真实模式：符合条件的岗位会发起 BOSS 平台沟通。' : '模拟模式：只编排动作，不会发起外部沟通。') : '默认处于模拟模式，先导入岗位或连接 BOSS，再开始编排。'; els.pause.textContent = els.enabled.checked ? '立即暂停' : '立即开始'; els.pause.classList.toggle('resume-button', !els.enabled.checked); }
  function renderLogs(logs) { els.logs.replaceChildren(); if (!logs.length) { els.logs.append(make('div', '还没有运行记录。导入或采集后，这里会留下每一步。', 'empty-state')); return; } logs.slice(0, 8).forEach(log => { const row = make('div', undefined, 'log-row'); row.append(make('span', timeLabel(first(log, ['created_at', 'timestamp', 'time'])), 'log-time'), make('span', safe(first(log, ['type', 'level'], 'INFO')).toUpperCase(), 'log-type'), make('span', safe(first(log, ['message', 'text', 'detail'], '')), 'log-message')); els.logs.append(row); }); }
  function renderAlert(data) {
    let box = $('#alertBanner');
    if (!box) { box = make('div'); box.id = 'alertBanner'; box.className = 'alert-banner'; els.banner.insertAdjacentElement('afterend', box); }
    const alerts = asArray(data.alerts);
    const paused = !(data.automation && data.automation.enabled);
    const latest = alerts[0];
    if (!latest || !paused) { box.style.display = 'none'; box.replaceChildren(); return; }
    box.style.display = 'flex';
    box.replaceChildren(make('strong', '需要你处理'), make('span', safe(latest.detail)), make('span', `· ${timeLabel(latest.created_at)}`));
  }
  function render(data) { state.data = data; state.jobs = data.jobs; if (state.selected) state.selected = state.jobs.find(j => j.id === state.selected.id) || null; renderStats(data); renderJobs(); renderDetail(); renderResume(data.profile); renderRules(data.rules); renderAutomation(data.automation, data.rules); renderLogs(data.logs); renderAlert(data); els.connection.replaceChildren(make('i'), make('span', '后端已连接')); }
  async function load() { if (state.formDirty) return; try { render(normalizeState(await api('/api/state'))); } catch (e) { els.connection.replaceChildren(make('i'), make('span', '连接失败')); toast(`无法加载状态：${e.message}`, true); } }
  function setBusy(value) { state.busy = value; els.app.classList.toggle('loading', value); }
  async function runOnce() { if (state.busy) return; setBusy(true); try { const result = await api('/api/run', { method: 'POST', body: '{}' }); const status = safe(first(result, ['status'], first(result.data || {}, ['status'], 'unknown'))); toast(`单轮状态：${status}`); await load(); } catch (e) { toast(e.message, true); } finally { setBusy(false); } }
  async function importText(text) { setBusy(true); try { let jobs = null; try { const parsed = JSON.parse(text); if (Array.isArray(parsed)) jobs = parsed; else if (parsed && Array.isArray(parsed.jobs)) jobs = parsed.jobs; } catch (_) {} const body = jobs ? { jobs } : { text }; await api('/api/import', { method: 'POST', body: JSON.stringify(body) }); toast('导入完成'); await load(); } catch (e) { toast(`导入失败：${e.message}`, true); } finally { setBusy(false); } }
  function csvToText(text) { const lines = text.split(/\r?\n/).filter(Boolean); if (!lines.length) return text; const heads = lines.shift().split(',').map(x => x.trim()); const jobs = lines.map(line => { const vals = line.split(','); return heads.reduce((obj, key, i) => { obj[key] = (vals[i] || '').trim(); return obj; }, {}); }); return JSON.stringify({ jobs }); }
  $$('.filter').forEach(button => button.addEventListener('click', () => { $$('.filter').forEach(x => x.classList.remove('active')); button.classList.add('active'); state.filter = button.dataset.filter; state.jobPage = 1; renderJobs(); }));
  els.search.addEventListener('input', () => { state.jobQuery = els.search.value; state.jobPage = 1; renderJobs(); });
  els.pageSize.addEventListener('change', () => { state.pageSize = Math.max(5, num(els.pageSize.value, 20)); state.jobPage = 1; renderJobs(); });
  $$('.nav-item').forEach(button => button.addEventListener('click', () => { $$('.nav-item').forEach(x => x.classList.remove('active')); button.classList.add('active'); $('#sidebar').classList.remove('open'); if (button.dataset.view === 'resume') els.resume.focus(); if (button.dataset.view === 'rules') $('#modeSelect').focus(); if (button.dataset.view === 'logs') $('#logList').scrollIntoView({ behavior: 'smooth' }); }));
  $$('[data-view="logs"]').forEach(button => button.addEventListener('click', () => $('#logList').scrollIntoView({ behavior: 'smooth' })));
  $('#openSidebar').addEventListener('click', () => $('#sidebar').classList.add('open')); $('#closeSidebar').addEventListener('click', () => $('#sidebar').classList.remove('open')); $('#refreshBtn').addEventListener('click', load);
  $('#importBtn').addEventListener('click', () => $('#fileInput').click()); $('#fileInput').addEventListener('change', async e => { const file = e.target.files[0]; if (!file) return; const text = await file.text(); await importText(text); e.target.value = ''; });
  $('#collectBtn').addEventListener('click', () => runAction('/api/browser/collect', {}, '采集任务已提交')); $('#analyzeAllBtn').addEventListener('click', () => runAction('/api/analyze', {}, '批量分析已提交')); $('#loginBtn').addEventListener('click', () => runAction('/api/browser/login', {}, 'BOSS 登录流程已启动，请查看 Edge')); $('#runBtn').addEventListener('click', runOnce); $('#modeSelect').addEventListener('change', () => { els.modeChip.textContent = els.mode.value === 'live' ? 'LIVE / BOSS' : 'DRY RUN'; });
  $('#saveResumeBtn').addEventListener('click', () => runAction('/api/profile', { resume_text: els.resume.value }, '简历已保存')); $('#saveRulesBtn').addEventListener('click', async () => { const rules = { titles: ruleList(rulesEls.titles.value), cities: ruleList(rulesEls.cities.value), districts: ruleList(rulesEls.districts.value), min_salary: num(rulesEls.minSalary.value, 0), max_salary: num(rulesEls.maxSalary.value, 0), skills: ruleList(rulesEls.skills.value), blacklist: ruleList(rulesEls.blacklist.value), company_min: rulesEls.companyMin.value.trim() ? num(rulesEls.companyMin.value, 0) : null, company_max: rulesEls.companyMax.value.trim() ? num(rulesEls.companyMax.value, 0) : null, recruitment_type: rulesEls.recruitment.value, max_education: rulesEls.education.value, greeting: rulesEls.greeting.value.trim() }; if (state.busy) return; setBusy(true); try { await api('/api/rules', { method: 'POST', body: JSON.stringify(rules) }); await api('/api/automation', { method: 'POST', body: JSON.stringify({ enabled: els.enabled.checked, mode: els.mode.value, daily_limit: num(els.dailyLimit.value, 10), interval_seconds: num(els.interval.value, 90), min_score: num(els.minScore.value, 70), auto_approve: els.autoApprove.checked, auto_collect: els.autoCollect.checked }) }); state.formDirty = false; toast('筛选与托管设置已保存'); await load(); } catch (e) { toast(e.message, true); } finally { setBusy(false); } });
  /* One-click toggle: the dispatcher checks the flag before every send, so nothing new starts. */
  $('#pauseBtn').addEventListener('click', async () => {
    if (state.busy) return;
    const turningOn = !els.enabled.checked;
    setBusy(true);
    try {
      const base = { ...(state.data && state.data.automation ? state.data.automation : {}) };
      const payload = {
        ...base,
        enabled: turningOn,
        mode: els.mode.value,
        daily_limit: num(els.dailyLimit.value, 150),
        interval_seconds: num(els.interval.value, 70),
        min_score: num(els.minScore.value, 55),
        auto_approve: els.autoApprove.checked,
        auto_collect: els.autoCollect.checked,
      };
      await api('/api/automation', { method: 'POST', body: JSON.stringify(payload) });
      els.enabled.checked = turningOn;
      state.formDirty = false;
      toast(turningOn ? '已开启托管：符合条件的岗位会继续派发' : '已暂停托管：正在进行的这一条会走完，之后不再派发');
      await load();
    } catch (e) { toast(e.message, true); } finally { setBusy(false); }
  });
  function selectJob(id) { state.selected = state.jobs.find(j => j.id === id) || null; renderJobs(); renderDetail(); }
  [els.resume, ...Object.values(rulesEls), els.mode, els.minScore, els.dailyLimit, els.interval, els.enabled, els.autoApprove, els.autoCollect].forEach(input => input.addEventListener('input', () => { state.formDirty = true; })); window.setInterval(() => { if (!state.busy) load(); }, 5000);
  load();
})();
