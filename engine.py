from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SHANGHAI = timezone(timedelta(hours=8))
TERMINAL = {'sent', 'blocked', 'uncertain', 'pending'}

# 千人以上公司只准入外资/外企：BOSS 岗位页不显示企业性质，用常见外企名单兜底。
# 命中规则是「公司名包含其中任意一项」，所以只放品牌词，不放「中国」「国际」这类泛词。
DEFAULT_FOREIGN_WHITELIST = [
    # 美资科技/软件
    '微软', 'microsoft', '亚马逊', 'amazon', '谷歌', 'google', '苹果公司', 'apple',
    '甲骨文', 'oracle', '思科', 'cisco', 'ibm', '英特尔', 'intel', '英伟达', 'nvidia',
    'amd', '高通', 'qualcomm', '德州仪器', '应用材料', 'asml', '赛默飞', 'thermo fisher',
    '安捷伦', 'agilent', '丹纳赫', 'danaher', '帕兰提尔', 'palantir', 'zoom',
    # 欧资工业/制造
    '西门子', 'siemens', '博世', 'bosch', '大陆集团', 'continental', '采埃孚', 'zf',
    '舍弗勒', 'schaeffler', '米其林', 'michelin', '施耐德', 'schneider', 'abb',
    '霍尼韦尔', 'honeywell', '飞利浦', 'philips', '通用电气', 'ge医疗', '3m中国',
    '杜邦', 'dupont', '陶氏', 'dow', '巴斯夫', 'basf', '拜耳', 'bayer', '赢创', 'evonik',
    '汉高', 'henkel', '蔡司', 'zeiss', '通快', 'trumpf', '库卡', 'kuka', '发那科', 'fanuc',
    '安川', 'yaskawa', '欧姆龙', 'omron', '基恩士', 'keyence', '罗克韦尔', 'rockwell',
    '艾默生', 'emerson', '江森自控', 'johnson controls', '开利', 'carrier',
    '奥的斯', 'otis', '蒂森克虏伯', 'thyssenkrupp', '迅达', 'schindler', '通力', 'kone',
    '沃尔沃', 'volvo', '佛吉亚', 'faurecia', '安波福', 'aptiv', '法雷奥', 'valeo',
    # 医药/化工/消费品
    '默克', 'merck', '辉瑞', 'pfizer', '罗氏', 'roche', '诺华', 'novartis',
    '赛诺菲', 'sanofi', '阿斯利康', 'astrazeneca', '葛兰素史克', 'gsk', '葛兰素',
    '强生', 'johnson & johnson', '礼来', 'lilly', '诺和诺德', 'novo nordisk',
    '雅培', 'abbott', '美敦力', 'medtronic', '波士顿科学', '史赛克', 'stryker',
    '雀巢', 'nestle', '联合利华', 'unilever', '宝洁', 'procter', '可口可乐', 'coca-cola',
    '百事', 'pepsico', '麦当劳', 'mcdonald', '星巴克', 'starbucks', '宜家', 'ikea',
    '耐克', 'nike', '阿迪达斯', 'adidas', '欧莱雅', "l'oreal", '资生堂', 'shiseido',
    '迪卡侬', 'decathlon', '达能', 'danone', '亿滋', 'mondelez', '玛氏', 'mars',
    '费列罗', 'ferrero', '金佰利', 'kimberly', '高露洁', 'colgate', '喜力', 'heineken',
    '嘉士伯', 'carlsberg', '雅诗兰黛', 'estee lauder', 'lvmh', '开云', 'kering',
    # 汽车/新能源
    '特斯拉', 'tesla', '大众汽车', 'volkswagen', '上汽大众', '一汽大众',
    '宝马', 'bmw', '奔驰', 'mercedes', '奥迪', 'audi', '丰田', 'toyota',
    '本田', 'honda', '日产汽车', 'nissan', '现代汽车', 'hyundai', '起亚', 'kia',
    # 日韩电子
    '松下', 'panasonic', '索尼', 'sony', '佳能', 'canon', '尼康', 'nikon',
    '三星', 'samsung', 'lg电子', '富士通', 'fujitsu', 'nec', '日立', 'hitachi',
    '东芝', 'toshiba', '村田', 'murata', 'tdk', '爱普生', 'epson', '岛津', 'shimadzu',
    # 通信/金融/咨询
    '爱立信', 'ericsson', '诺基亚', 'nokia', '汇丰', 'hsbc', '渣打', 'standard chartered',
    '花旗', 'citi', '摩根大通', 'jpmorgan', '摩根士丹利', 'morgan stanley',
    '高盛', 'goldman', '瑞银', 'ubs', '安联', 'allianz', '安盛', 'axa', '友邦', 'aia',
    '麦肯锡', 'mckinsey', '波士顿咨询', 'bcg', '贝恩', 'bain', '罗兰贝格', 'roland berger',
    '德勤', 'deloitte', '普华永道', 'pwc', '安永', 'ernst & young', '毕马威', 'kpmg',
    '埃森哲', 'accenture', '凯捷', 'capgemini', '印孚瑟斯', 'infosys', '塔塔咨询', 'tata',
    '索迪斯', 'sodexo', '仲量联行', 'jll', '世邦魏理仕', 'cbre', '戴德梁行', 'cushman',
    '联邦快递', 'fedex', 'dhl', '马士基', 'maersk',
    # 亚太外企（上海/杭州常见）
    'coupang', 'grab', 'shopee', 'lazada', 'sea group', 'booking', 'agoda',
    '野村', 'nomura', '三菱商事', '伊藤忠', '丸红', '住友商事', '日立制作所',
    '新加坡科技', 'dbs', 'ocbc', '大华银行',
]


def now():
    return datetime.now(timezone.utc).isoformat()


class ValidationError(ValueError):
    pass


def number(value, name, low, high):
    if isinstance(value, bool):
        raise ValidationError(f'{name} 必须是数字')
    try:
        value = float(value)
    except (ValueError, TypeError):
        raise ValidationError(f'{name} 必须是数字') from None
    if not math.isfinite(value) or not low <= value <= high:
        raise ValidationError(f'{name} 必须在 {low}–{high} 之间')
    return value


class JobEngine:
    def __init__(self, db_path='job_pilot.sqlite3'):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=30000')
        db.execute('PRAGMA journal_mode=WAL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def _init_db(self):
        with self._connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK(id=1), resume_text TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS rules (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS automation (id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL DEFAULT 0, mode TEXT NOT NULL DEFAULT 'dry_run', daily_limit INTEGER NOT NULL DEFAULT 10, interval_seconds INTEGER NOT NULL DEFAULT 90, min_score REAL NOT NULL DEFAULT 60);
            CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, external_id TEXT UNIQUE, data TEXT NOT NULL, score REAL, reason TEXT, status TEXT NOT NULL DEFAULT 'new', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS drafts (job_id INTEGER PRIMARY KEY REFERENCES jobs(id), text TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER, event TEXT NOT NULL, detail TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL UNIQUE, mode TEXT NOT NULL, outcome TEXT NOT NULL, detail TEXT, created_at TEXT NOT NULL);
            INSERT OR IGNORE INTO rules(id,data,updated_at) VALUES(1,'{}',datetime('now'));
            INSERT OR IGNORE INTO automation(id) VALUES(1);
            ''')
            for table, column, ddl in [('jobs', 'analysis', "TEXT NOT NULL DEFAULT '{}'"),
                                        ('automation', 'auto_approve', 'INTEGER NOT NULL DEFAULT 0'),
                                        ('automation', 'auto_collect', 'INTEGER NOT NULL DEFAULT 0')]:
                columns = {r['name'] for r in db.execute(f'PRAGMA table_info({table})')}
                if column not in columns:
                    db.execute(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}')
            # An interrupted live attempt may already have reached the platform.
            db.execute("UPDATE jobs SET status='uncertain' WHERE id IN (SELECT job_id FROM attempts WHERE mode='live' AND outcome='pending')")
            db.execute("UPDATE attempts SET outcome='uncertain', detail=COALESCE(detail,'') || '（进程中断，结果待人工核对，不会自动重试）' "
                       "WHERE mode='live' AND outcome='pending'")

    def _one(self, sql, args=()):
        with self._connect() as db:
            return db.execute(sql, args).fetchone()

    @staticmethod
    def _json(value):
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}

    def _invalidate(self, db):
        db.execute("UPDATE drafts SET approved=0 WHERE job_id IN (SELECT id FROM jobs WHERE status NOT IN ('sent','blocked','uncertain','pending'))")
        db.execute("UPDATE jobs SET score=NULL,reason=NULL,analysis='{}',status='new' WHERE status NOT IN ('sent','blocked','uncertain','pending')")

    def set_profile(self, resume_text):
        if not isinstance(resume_text, str) or len(resume_text) > 200000:
            raise ValidationError('简历文本必须是 200000 字符以内的文本')
        with self._lock, self._connect() as db:
            old = db.execute('SELECT resume_text FROM profile WHERE id=1').fetchone()
            db.execute('INSERT INTO profile VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET resume_text=excluded.resume_text,updated_at=excluded.updated_at', (resume_text, now()))
            if old and old[0] != resume_text:
                self._invalidate(db)
        return self.get_profile()

    def get_profile(self):
        row = self._one('SELECT resume_text,updated_at FROM profile WHERE id=1')
        return dict(row) if row else {'resume_text': '', 'updated_at': None}

    def set_rules(self, rules):
        if not isinstance(rules, dict):
            raise ValidationError('规则必须是 JSON 对象')
        clean = self.get_rules()['data']
        for key in ('cities', 'titles', 'blacklist', 'skills', 'districts', 'collect_titles', 'exclude_titles', 'foreign_whitelist'):
            if key in rules:
                values = rules[key]
                cap = 400 if key == 'foreign_whitelist' else 100
                if not isinstance(values, list) or len(values) > cap or any(not isinstance(x, str) or len(x) > 100 for x in values):
                    raise ValidationError(f'{key} 必须是字符串数组（最多{cap}项）')
                clean[key] = list(dict.fromkeys(x.strip() for x in values if x.strip()))
                if key == 'collect_titles':
                    clean[key] = clean[key][:40]
        for key in ('min_salary', 'max_salary'):
            if key in rules:
                clean[key] = number(rules[key], key, 0, 1000)
        for key in ('company_min', 'company_max'):
            if key in rules:
                if rules[key] in (None, ''):
                    clean.pop(key, None)
                    continue
                value = number(rules[key], key, 0, 1000000)
                if value != int(value):
                    raise ValidationError(f'{key} 必须是整数')
                clean[key] = int(value)
        for key in ('tiny_needs_funding', 'large_needs_foreign', 'accept_near_miss', 'allow_unknown_salary',
                    'dedupe_companies'):
            if key in rules:
                clean[key] = bool(rules[key])
        if 'recruitment_type' in rules:
            if rules['recruitment_type'] in (None, ''):
                clean.pop('recruitment_type', None)
            elif rules['recruitment_type'] not in ('social',):
                raise ValidationError('招聘类型仅支持 social')
            else:
                clean['recruitment_type'] = rules['recruitment_type']
        if 'max_education' in rules:
            if rules['max_education'] in (None, ''):
                clean.pop('max_education', None)
            elif rules['max_education'] not in ('不限', '初中', '中专', '高中', '大专', '本科', '硕士', '博士'):
                raise ValidationError('最高学历不受支持')
            else:
                clean['max_education'] = rules['max_education']
        if 'greeting' in rules:
            greeting = rules['greeting']
            if greeting in (None, ''):
                clean.pop('greeting', None)
            elif not isinstance(greeting, str) or len(greeting) > 2000:
                raise ValidationError('招呼语模板须为 2000 字以内的文本')
            else:
                clean['greeting'] = greeting.strip()
        if clean.get('company_max') and clean.get('company_min', 0) > clean['company_max']:
            raise ValidationError('公司规模下限不可高于上限')
        if clean.get('max_salary') and clean.get('min_salary', 0) > clean['max_salary']:
            raise ValidationError('薪资下限不可高于上限（单位 K/月）')
        with self._lock, self._connect() as db:
            old = self.get_rules()['data']
            db.execute('UPDATE rules SET data=?,updated_at=? WHERE id=1', (json.dumps(clean, ensure_ascii=False), now()))
            if clean != old:
                self._invalidate(db)
        return clean

    def get_rules(self):
        row = self._one('SELECT data,updated_at FROM rules WHERE id=1')
        return {'data': self._json(row[0]), 'updated_at': row[1]}

    def set_automation(self, data):
        cfg = self.get_automation()
        for key in cfg:
            if key in data:
                cfg[key] = data[key]
        if cfg['mode'] not in ('dry_run', 'live'):
            raise ValidationError('运行模式必须是 dry_run 或 live')
        for key in ('enabled', 'auto_approve', 'auto_collect'):
            if not isinstance(cfg[key], bool):
                raise ValidationError(f'{key} 必须是布尔值')
        cfg['daily_limit'] = int(number(cfg['daily_limit'], '每日上限', 1, 200))
        cfg['interval_seconds'] = int(number(cfg['interval_seconds'], '间隔秒数', 60 if cfg['mode'] == 'live' else 10, 86400))
        cfg['min_score'] = number(cfg['min_score'], '最低评分', 0, 100)
        with self._lock, self._connect() as db:
            db.execute('UPDATE automation SET enabled=?,mode=?,daily_limit=?,interval_seconds=?,min_score=?,auto_approve=?,auto_collect=? WHERE id=1',
                       tuple(cfg[k] for k in ('enabled', 'mode', 'daily_limit', 'interval_seconds', 'min_score', 'auto_approve', 'auto_collect')))
        self.log('automation', f"托管{'开启' if cfg['enabled'] else '暂停'}；模式 {cfg['mode']}")
        return cfg

    def get_automation(self):
        cfg = dict(self._one('SELECT enabled,mode,daily_limit,interval_seconds,min_score,auto_approve,auto_collect FROM automation WHERE id=1'))
        for key in ('enabled', 'auto_approve', 'auto_collect'):
            cfg[key] = bool(cfg[key])
        return cfg

    @staticmethod
    def canonical_url(url):
        if not url:
            return ''
        p = urlsplit(str(url).strip())
        query = '' if p.hostname in ('www.zhipin.com', 'zhipin.com') else p.query
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip('/'), query, ''))

    def import_jobs(self, jobs):
        if not isinstance(jobs, list) or len(jobs) > 1000:
            raise ValidationError('岗位应为数组，每次最多 1000 条')
        added = 0
        with self._connect() as db:
            for raw in jobs:
                if not isinstance(raw, dict):
                    raise ValidationError('每条岗位必须是对象')
                job = {key: str(raw.get(key) or '').strip()[:20000] for key in ('title', 'company', 'city', 'salary', 'description', 'url', 'source', 'company_size', 'education', 'experience', 'recruitment_type', 'financing', 'company_type')}
                job['title'] = job['title'] or str(raw.get('position') or '').strip()
                if not job['title']:
                    continue
                if not job['city']:
                    job['city'] = str(raw.get('location') or '')
                if not job['salary'] and raw.get('salary_min') is not None:
                    job['salary'] = f"{raw['salary_min']}-{raw.get('salary_max', raw['salary_min'])}K"
                canonical = self.canonical_url(job['url'])
                ext = canonical or str(raw.get('external_id') or raw.get('id') or '') or hashlib.sha256(json.dumps(job, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                payload = json.dumps(job, ensure_ascii=False)
                cur = db.execute('INSERT OR IGNORE INTO jobs(external_id,data,created_at,updated_at) VALUES(?,?,?,?)', (ext, payload, now(), now()))
                if cur.rowcount:
                    added += cur.rowcount
                else:
                    existing = db.execute('SELECT id,data,status FROM jobs WHERE external_id=?', (ext,)).fetchone()
                    old_data = self._json(existing['data']) if existing else {}
                    changed = False
                    for key in ('salary', 'city', 'company_size', 'education', 'experience', 'recruitment_type', 'financing', 'company_type'):
                        if job.get(key) and not old_data.get(key):
                            old_data[key] = job[key]
                            changed = True
                    # A placeholder summary may be replaced by the full posting text.
                    if job.get('description') and ('【列表摘要' in str(old_data.get('description', '')) or len(job['description']) > len(str(old_data.get('description', ''))) + 40):
                        if job['description'] != old_data.get('description'):
                            old_data['description'] = job['description']
                            changed = True
                    if changed:
                        db.execute('UPDATE jobs SET data=?,score=NULL,reason=NULL,analysis=\'{}\',status=CASE WHEN status NOT IN (\'sent\',\'blocked\',\'uncertain\',\'pending\') THEN \'new\' ELSE status END,updated_at=? WHERE id=?',
                                   (json.dumps(old_data, ensure_ascii=False), now(), existing['id']))
                        db.execute('UPDATE drafts SET approved=0 WHERE job_id=? AND ? NOT IN (\'sent\',\'blocked\',\'uncertain\',\'pending\')', (existing['id'], existing['status']))
        self.log('import', f'导入 {added} 条，重复或空标题 {len(jobs)-added} 条')
        return {'added': added, 'total': len(jobs), 'duplicates': len(jobs)-added}

    def parse_import_text(self, text):
        if not isinstance(text, str) or len(text) > 2000000:
            raise ValidationError('导入文本过长或格式错误')
        text = text.lstrip('\ufeff').strip()
        if text.startswith(('[', '{')):
            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                raise ValidationError('JSON 格式不正确') from None
            return self.import_jobs(obj if isinstance(obj, list) else obj.get('jobs'))
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or not {'title', 'position'}.intersection(reader.fieldnames):
            raise ValidationError('CSV 需要 title 字段')
        return self.import_jobs(list(reader))

    def _job(self, jid):
        row = self._one('SELECT * FROM jobs WHERE id=?', (jid,))
        if not row:
            return None
        job = self._json(row['data'])
        job.update({k: row[k] for k in ('id', 'score', 'reason', 'status')})
        job.update(self._json(row['analysis']))
        draft = self._one('SELECT text,approved FROM drafts WHERE job_id=?', (jid,))
        attempt = self._one('SELECT mode,outcome,detail,created_at FROM attempts WHERE job_id=?', (jid,))
        job.update(draft=draft['text'] if draft else '', approved=bool(draft['approved']) if draft else False, attempt=dict(attempt) if attempt else None)
        return job

    @staticmethod
    def _funded(job):
        """True only when there is visible funding evidence (0-20 人必须融过资)."""
        stage = str(job.get('financing') or '')
        if stage and any(x in stage for x in ('未融资', '不需要融资')):
            return False
        pattern = r'(未融资|不需要融资|天使轮|pre-?a轮|a\+?轮|b\+?轮|c\+?轮|d\+?轮|e轮|f轮|战略融资|已上市|融资|风投)'
        if re.search(pattern, (stage + ' ' + str(job.get('company_size') or '')).lower()):
            return not re.search(r'未融资|不需要融资', stage)
        # 融资信息有时只写在公司介绍里，宁可算"有"也不因为读不到就误杀
        body = str(job.get('description') or '')[:3000].lower()
        return bool(re.search(r'(天使轮|pre-?a轮|a轮|b轮|c轮|战略融资|已上市|完成.{0,6}融资|获得.{0,6}融资)', body))

    @staticmethod
    def _foreign_company(job, whitelist=None):
        """千家以上公司只准入外资/外企：企业性质字段、公司名证据，或外企白名单。"""
        company = str(job.get('company') or '')
        text = ' '.join(str(job.get(k) or '') for k in ('company', 'company_type', 'financing'))
        if str(job.get('company_type') or '').strip():
            if re.search(r'(外商独资|外资|中外合资|外企|跨国)', text):
                return True
        elif re.search(r'(外商独资|外资企业|外企|跨国公司|中外合资|\(中国\)|（中国）)', text):
            return True
        hay = company.lower()
        for name in (whitelist if whitelist is not None else DEFAULT_FOREIGN_WHITELIST):
            token = str(name).strip().lower()
            if not token:
                continue
            if token.isascii() and len(token) <= 4:
                # 短英文名（3M/TDK/UPS 之类）按词边界匹配，避免命中 Groups/Connect 这类词
                if re.search(r'(?<![a-z0-9])' + re.escape(token) + r'(?![a-z0-9])', hay):
                    return True
            elif token in hay:
                return True
        return False

    @staticmethod
    def _company_band(value):
        text = str(value or '').replace(',', '').replace('，', '').replace('人', '').strip()
        if not text:
            return None
        if re.search(r'\d+\s*万', text):
            return None
        nums = [int(x) for x in re.findall(r'\d+', text)]
        if not nums:
            return None
        if any(x in text for x in ('以上', '+')):
            return nums[0], float('inf')
        if '以下' in text:
            return 0, nums[0]
        return (nums[0], nums[1] if len(nums) > 1 else nums[0])

    @staticmethod
    def _education_level(value):
        text = str(value or '').strip().replace('学历不限', '不限')
        levels = ('不限', '初中', '中专', '高中', '大专', '本科', '硕士', '博士')
        if not text:
            return None
        found = [(i, level) for i, level in enumerate(levels[1:], 1) if level in text]
        if found:
            return min(i for i, _ in found)
        return 0 if '不限' in text else None

    @staticmethod
    def _social_job(job):
        evidence = ' '.join(str(job.get(k, '')) for k in ('title', 'experience')).lower()
        description = str(job.get('description', '')).lower()
        description = re.sub(r'(接受|欢迎|允许|不限|均可)\s*应届生?', '', description)
        # "接受应届 / 欢迎应届 / 应届也可 / 可校招" still hires experienced people; only
        # campus-only wording blocks. Strip the soft forms before looking for campus words.
        evidence = re.sub(r'(接受|欢迎|允许|可|不限|均可|也能|也要|同时)\s*(?:应届生?|校招生?|校园招聘)', '', evidence)
        if (any(x in evidence for x in ('校园', '校招', '应届', '在校', '实习', '兼职', '临时', 'campus', 'internship'))
                or re.search(r'(?:面向|仅限|招聘|招募|要求|工作周期).{0,12}(?:应届|在校|校招|校园招聘|实习生|兼职|临时)', description)):
            return False
        kind = str(job.get('recruitment_type', '')).strip().lower()
        if kind in ('social', '社招', '社会招聘', '社会招募'):
            return True
        if kind in ('campus', 'internship', '校园', '校园招聘', '校招', '应届', '应届生', '实习'):
            # BOSS 会把"可校招 / 接受应届"的社招岗也打上 campus 标签。只有当标题或开头
            # 明确写了"可校招/接受应届"、而且职级不是学生口径时才按社招放行。
            head = (str(job.get('title', '')) + ' ' + str(job.get('description', ''))[:300]).lower()
            soft = re.search(r'(?:可|接受|欢迎|允许|同时|也)\s*(?:校招|应届生?|校园招聘)', head)
            exp = str(job.get('experience', '')).strip()
            if soft and '年' in exp and '在校' not in exp and '应届' not in exp:
                return True
            return False
        exp = str(job.get('experience', '')).strip()
        if exp and any(x in exp for x in ('经验不限', '无需经验', '1-3年', '1年以上', '3-5年', '5-10年', '10年以上')):
            return True
        return None

    @staticmethod
    def _outsourced(job):
        """Reject staffing-agency and dispatched/outsourced postings."""
        company = str(job.get('company') or '').lower()
        title = str(job.get('title') or '').lower()
        description = str(job.get('description') or '').lower()
        agency = ('科锐', '外企德科', '德科', '万宝盛华', '任仕达', '埃摩森', '米高蒲志', '翰德', '锐仕方达',
                  '猎聘', '智联招聘', '前程无忧', '中智', '上海外服', 'fesco', 'adecco', 'manpower', 'randstad',
                  '人力外包', '人才外包', '劳务派遣', '猎头',
                  # 大型人力/外包服务商：岗位多为派驻，公司名不带"外包"字样
                  '软通', '中软国际', '博彦', '文思海辉', '中电金信', '佰钧成', '法本信息', '中科软')
        if any(name in company for name in agency):
            return '招聘方为人力/外包服务机构'
        body = f'{title} {description}'
        if any(word in body for word in ('非外包', '不外包', '无外包', '非驻场', '不驻场')):
            return None
        if any(word in body for word in ('外包', '驻场', '派遣', '劳务', '人力外派')):
            return '岗位描述显示为外包/驻场/派遣'
        return None

    @staticmethod
    def match_job(job, resume, rules):
        title = str(job.get('title', job.get('position', ''))).lower()
        city = str(job.get('city', job.get('location', ''))).lower()
        # Stack mentions in a JD (阿里云/腾讯云…) must not count as working for them.
        text = ' '.join(str(job.get(k, '')) for k in ('title', 'company')).lower()
        full_text = ' '.join(str(job.get(k, '')) for k in ('title', 'description', 'company', 'city')).lower()
        notes = []
        if 'company_min' in rules or 'company_max' in rules:
            band = JobEngine._company_band(job.get('company_size'))
            if band is None:
                # The list card often hides company size; do not drop the job for that alone.
                notes.append('公司规模待核验')
            else:
                low_bound = float(rules.get('company_min', 0))
                high_bound = float(rules.get('company_max', float('inf')))
                if band[0] < low_bound or band[1] > high_bound:
                    return -1, '公司规模不符合规则'
                if rules.get('tiny_needs_funding') and band[1] <= 20 and not JobEngine._funded(job):
                    return -1, '公司规模 0-20 人且没有融资记录，需人工核对'
                if rules.get('large_needs_foreign') and band[0] >= 1000 and not JobEngine._foreign_company(job, rules.get('foreign_whitelist')):
                    return -1, '千人以上公司只准入外资/外企，该公司未确认为外资'
        if rules.get('recruitment_type') == 'social':
            social = JobEngine._social_job(job)
            if social is None:
                return -1, '招聘类型缺失或无法确认，需人工核对'
            if not social:
                return -1, '仅限社会招聘，排除校园/应届/实习'
        if 'max_education' in rules:
            level = JobEngine._education_level(job.get('education'))
            if level is None:
                return -1, '学历要求缺失或无法确认，需人工核对'
            max_level = float('inf') if rules['max_education'] == '不限' else JobEngine._education_level(rules['max_education'])
            if level > max_level:
                return -1, '学历要求超过最高学历'
        if rules.get('cities') and not any(x.lower() in city for x in rules['cities']):
            return -1, '城市不符合规则或城市缺失'
        if any(x.lower() in text for x in rules.get('blacklist', [])):
            return -1, '命中黑名单'
        outsourced = JobEngine._outsourced(job)
        if outsourced:
            return -1, outsourced
        # BOSS titles vary in spacing ("AI 应用开发" vs "AI应用开发"), so compare without blanks.
        title_compact = re.sub(r'[\s\u3000]+', '', title)
        if rules.get('titles') and not any(
                re.sub(r'[\s\u3000]+', '', str(x).lower()) in title_compact for x in rules['titles']):
            return -1, '职位不符合规则'
        if any(x.lower() in title for x in rules.get('exclude_titles', [])):
            return -1, '职位方向不符（非研发岗）'
        salary = str(job.get('salary', job.get('salary_min', ''))).strip()
        nums = re.findall(r'\d+(?:\.\d+)?', salary.split('·')[0])
        # BOSS renders salary with a private-use font, so the text is often unreadable.
        # An unknown figure no longer blocks the job; it is surfaced as 待核验 instead.
        salary_unknown = not nums or '面议' in salary or any(x in salary for x in ('天', '时', '年', '万'))
        if not salary_unknown:
            low = float(nums[0])
            high = float(nums[-1]) if len(nums) > 1 else low
            if low >= 1000 and not re.search('[kK]', salary):
                low /= 1000
                high = max(low, high / 1000)
            floor = float(rules.get('min_salary', 0) or 0)
            cap = float(rules.get('max_salary', 0) or 0)
            # Ranges only need to overlap the wanted band: 18-30K overlaps 20-30K, 35-60K does not.
            if cap and low > cap:
                return -1, f'薪资区间 {low:g}-{high:g}K 高于 {cap:g}K'
            if floor and high < floor:
                return -1, f'薪资区间 {low:g}-{high:g}K 低于 {floor:g}K'
        skills = [s for s in rules.get('skills', []) if s.lower() in resume.lower()]
        found = [s for s in skills if s.lower() in full_text]
        score = round(min(100, 40 + 60 * len(found) / max(1, min(4, len(skills)))), 1) if resume.strip() else 0
        reason = '匹配技能：' + '、'.join(found) if found else '硬条件通过，技能证据不足，请核对完整 JD'
        if '【列表摘要' in str(job.get('description', '')):
            reason += '；仅有列表摘要，完整要求需核对'
        if salary_unknown:
            reason += '；薪资未公开显示，需在沟通中确认'
        if notes:
            reason += '；' + '；'.join(notes)
        return score, reason

    def analyze(self, jid=None, ai_analyzer=None):
        with self._connect() as db:
            if jid is not None:
                ids = [int(jid)]
            else:
                # Always clear the backlog of unseen postings first, then refresh recent scores.
                ids = [r[0] for r in db.execute("SELECT id FROM jobs WHERE status='new' ORDER BY id DESC LIMIT 400")]
                if not ids:
                    ids = [r[0] for r in db.execute('SELECT id FROM jobs ORDER BY id DESC LIMIT 200')]
        results = []
        for job_id in ids:
            with self._lock:
                job = self._job(job_id)
                if not job:
                    raise ValidationError('岗位不存在')
                profile = self.get_profile()['resume_text']
                rules = self.get_rules()['data']
                local_score, reason = self.match_job(job, profile, rules)
                meta = {'analysis_source': 'local', 'risks': [], 'missing_skills': []}
                score = local_score
                found = [s for s in rules.get('skills', []) if s.lower() in profile.lower() and s.lower() in job.get('description', '').lower()]
                draft = '您好，我对贵公司的' + job['title'] + '岗位感兴趣。' + ('我的经历涉及' + '、'.join(found[:4]) + '，' if found else '') + '希望有机会进一步沟通。'
                if local_score >= 0 and ai_analyzer is not None and profile.strip():
                    try:
                        analysis = ai_analyzer(job, profile)
                        score, reason, draft = analysis['score'], analysis['reason'], analysis['draft']
                        meta.update(analysis_source='ai', risks=analysis['risks'], missing_skills=analysis['missing_skills'])
                    except Exception:
                        meta['risks'].append('AI 服务不可用或返回格式无效，已回退本地规则；未根据无效输出执行任何操作。')
                        meta['analysis_source'] = 'local_fallback'
                status = job['status'] if job['status'] in TERMINAL else ('matched' if score >= 0 else 'rejected')
                with self._connect() as db:
                    db.execute('UPDATE jobs SET score=?,reason=?,status=?,analysis=?,updated_at=? WHERE id=?', (score, reason, status, json.dumps(meta, ensure_ascii=False), now(), job_id))
                    # Reanalysis revokes old approval: the user must review the new evidence.
                    if job['status'] not in TERMINAL:
                        db.execute('INSERT INTO drafts VALUES(?,?,0,?) ON CONFLICT(job_id) DO UPDATE SET text=excluded.text,approved=0,updated_at=excluded.updated_at', (job_id, draft, now()))
                results.append(self._job(job_id))
        self.log('analysis', f'已分析 {len(results)} 条岗位')
        return results[0] if jid is not None else results

    DEFAULT_GREETING = (
        '补一句背景：那个 2.8 万行平台，从需求拆解、写码、自测到 Code Review，'
        '我基本是用 Claude Code / Codex 这类编程 Agent 协同完成的，MCP 工具接入、'
        'Subagent 编排也都在生产环境跑过。如果你们正打算把 Agent 落到业务里，'
        '我可以直接讲清楚哪些场景能落地、哪些是坑。'
    )
    def render_greeting(self, job):
        """Build the BOSS greeting from the rules template, filling in job facts."""
        template = self.get_rules()['data'].get('greeting') or self.DEFAULT_GREETING
        values = {
            'title': str(job.get('title') or '这个岗位'),
            'company': str(job.get('company') or '贵司'),
            'city': str(job.get('city') or ''),
        }
        text = template
        for key, value in values.items():
            text = text.replace('{' + key + '}', value)
        return text.strip()

    def approve(self, jid, text=None):
        with self._lock:
            job = self._job(jid)
            if not job:
                raise ValidationError('岗位不存在')
            if job['score'] is None or job['score'] < 0:
                raise ValidationError('请先分析岗位；硬筛拒绝的岗位不可入队')
            if job['status'] in TERMINAL:
                raise ValidationError('该岗位已执行或结果待核对，不可重复入队')
            if self.match_job(job, self.get_profile()['resume_text'], self.get_rules()['data'])[0] < 0:
                raise ValidationError('岗位已不符合当前规则，请重新分析')
            text = job['draft'] if text is None else text
            if text is None or not str(text).strip():
                text = self.render_greeting(job)
            if not isinstance(text, str) or not text.strip() or len(text) > 5000:
                raise ValidationError('草稿须为 1–5000 字符的文本')
            with self._connect() as db:
                db.execute('INSERT INTO drafts VALUES(?,?,1,?) ON CONFLICT(job_id) DO UPDATE SET text=excluded.text,approved=1,updated_at=excluded.updated_at', (jid, text.strip(), now()))
                db.execute("UPDATE jobs SET status='approved' WHERE id=?", (jid,))
            self.log('approved', '已审核入队，尚未发起外部沟通', jid)
            return {'job_id': jid, 'text': text.strip(), 'approved': True}

    @staticmethod
    def district_rank(job, rules):
        """Lower is better: earlier listed districts win, unlisted ones sort last."""
        preferred = [str(x).strip() for x in rules.get('districts', []) if str(x).strip()]
        if not preferred:
            return 0
        area = str(job.get('city', ''))
        for index, name in enumerate(preferred):
            if name in area:
                return index
        return len(preferred) + 1

    def queue(self, min_score=0, mode=None):
        sql = "SELECT j.*,d.text,d.approved FROM jobs j JOIN drafts d ON d.job_id=j.id WHERE d.approved=1 AND j.status NOT IN ('sent','blocked','uncertain','pending') AND j.score>=? AND NOT EXISTS(SELECT 1 FROM attempts a WHERE a.job_id=j.id AND a.mode='live')"
        args = [min_score]
        if mode == 'dry_run':
            sql += ' AND NOT EXISTS(SELECT 1 FROM attempts a WHERE a.job_id=j.id)'
        with self._connect() as db:
            rows = [dict(r) | {'data': self._json(r['data']), 'approved': bool(r['approved'])} for r in db.execute(sql, args)]
        rules = self.get_rules()['data']
        # Never open a second conversation with a company we already greeted recently,
        # even when it publishes a different posting with a different URL.
        contacted = self.contacted_companies()
        rows = [r for r in rows if self._company_key(r['data'].get('company')) not in contacted]
        # Prefer the user's district order first, then the best score.
        rows.sort(key=lambda j: (self.district_rank(j, rules), -float(j['score'] or 0), j['id']))
        return rows

    @staticmethod
    def _company_key(name):
        return re.sub(r'[\s\u3000]+', '', str(name or ''))

    def contacted_companies(self, within_days=30):
        """Companies already greeted inside the window, keyed by normalised name.

        dedupe_companies 关闭时返回空集合：只按岗位（URL/attempt）去重，不做公司级拦截。
        """
        if not self.get_rules()['data'].get('dedupe_companies', True):
            return set()
        cutoff = (datetime.now(SHANGHAI) - timedelta(days=within_days)).astimezone(timezone.utc).isoformat()
        with self._connect() as db:
            rows = db.execute("SELECT j.data FROM attempts a JOIN jobs j ON j.id=a.job_id "
                              "WHERE a.mode='live' AND a.outcome IN ('sent','uncertain','blocked') "
                              "AND a.created_at>=?", (cutoff,)).fetchall()
        return {self._company_key(self._json(r['data']).get('company')) for r in rows} - {''}

    def skip(self, jid, reason):
        """Park a job that should not be queued, keeping the reason visible on the board."""
        with self._connect() as db:
            db.execute("UPDATE jobs SET status='rejected', reason=?, updated_at=? WHERE id=?", (reason, now(), jid))
        self.log('skipped', reason, jid)
        return {'job_id': jid, 'skipped': True}

    def record_attempt(self, jid, mode, outcome, detail=''):
        with self._connect() as db:
            old = db.execute('SELECT mode FROM attempts WHERE job_id=?', (jid,)).fetchone()
            if old and old[0] == 'live':
                raise ValidationError('该岗位已有真实尝试，不可重复执行')
            db.execute('INSERT INTO attempts(job_id,mode,outcome,detail,created_at) VALUES(?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET mode=excluded.mode,outcome=excluded.outcome,detail=excluded.detail,created_at=excluded.created_at', (jid, mode, outcome, detail, now()))
            db.execute('UPDATE jobs SET status=? WHERE id=?', ('pending' if mode == 'live' else 'simulated', jid))

    def finish_attempt(self, jid, outcome, detail):
        with self._connect() as db:
            db.execute('UPDATE attempts SET outcome=?,detail=? WHERE job_id=?', (outcome, detail, jid))
            db.execute('UPDATE jobs SET status=?,updated_at=? WHERE id=?', (outcome, now(), jid))
        self.log(outcome, detail, jid)

    def day_usage(self, mode='live'):
        start = datetime.now(SHANGHAI).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()
        return self._one('SELECT count(*) FROM attempts WHERE mode=? AND created_at>=?', (mode, start))[0]

    def last_attempt(self, mode):
        return self._one('SELECT created_at FROM attempts WHERE mode=? ORDER BY created_at DESC LIMIT 1', (mode,))

    def log(self, event, detail='', jid=None):
        with self._connect() as db:
            db.execute('INSERT INTO logs(job_id,event,detail,created_at) VALUES(?,?,?,?)', (jid, event, str(detail)[:3000], now()))

    def state(self):
        with self._connect() as db:
            jobs = [self._job(r[0]) for r in db.execute('SELECT id FROM jobs ORDER BY id DESC')]
            logs = [dict(r) for r in db.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 200')]
        cfg = self.get_automation()
        alerts = [row for row in logs if row['event'] in ('alert', 'login_required')][:3]
        return {'profile': self.get_profile(), 'rules': self.get_rules()['data'], 'jobs': jobs, 'logs': logs,
                'automation': cfg, 'alerts': alerts,
                'stats': {'jobs': len(jobs), 'pending': sum(j['status'] == 'new' for j in jobs), 'shortlisted': sum(j['approved'] and j['status'] not in TERMINAL for j in jobs),
                          'sent': sum(j['status'] == 'sent' for j in jobs), 'today_remaining': max(0, cfg['daily_limit'] - self.day_usage(cfg['mode'])), 'daily_limit': cfg['daily_limit'],
                          'attempts': self._one('SELECT count(*) FROM attempts')[0]}}
