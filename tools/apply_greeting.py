from engine import JobEngine

engine = JobEngine('data/job_pilot.sqlite3')
for job in engine.state()['jobs']:
    if job['status'] != 'approved':
        continue
    text = engine.render_greeting(job)
    engine.approve(job['id'], text)
    print(job['id'], job['company'], job['title'])
    print(text)
    print('---')
