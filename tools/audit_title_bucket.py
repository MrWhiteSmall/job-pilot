import json
import re
import sqlite3
from collections import Counter

db = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
db.row_factory = sqlite3.Row
rows = db.execute("SELECT * FROM jobs WHERE status='rejected'").fetchall()

buckets = Counter()
samples = {}
for r in rows:
    data = json.loads(r['data'])
    reason = (r['reason'] or '').split('：')[0]
    if reason != '职位不符合规则':
        continue
    title = str(data.get('title') or '')
    low = title.lower()
    if re.search(r'产品|运营|销售|市场|商务|客服|行政|人事|财务|设计|测试|运维|实施|交付|售前|讲师|顾问|总监|经理|主管', low):
        bucket = '非研发岗（被漏放进来才轮到这里）'
    elif 'python' in low:
        bucket = 'Python 开发'
    elif 'java' in low or 'go' in low.split() or '后端' in low or '服务端' in low:
        bucket = '后端/Java'
    elif '算法' in low or '大模型' in low or 'llm' in low or 'nlp' in low or '机器学习' in low or 'ai' in low:
        bucket = '算法/AI'
    elif '全栈' in low or '前端' in low:
        bucket = '全栈/前端'
    else:
        bucket = '其他'
    buckets[bucket] += 1
    samples.setdefault(bucket, []).append((r['id'], title, data.get('company')))

for bucket, count in buckets.most_common():
    print(bucket, count)
    for sid, title, company in samples[bucket][:6]:
        print('   ', sid, title, '|', company)
