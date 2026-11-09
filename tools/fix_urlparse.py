from pathlib import Path

path = Path(r'D:\DesktopCode\job-pilot\app.py')
text = path.read_text(encoding='utf-8')
before = text
text = text.replace('from urllib.parse import urlsplit', 'from urllib.parse import urlparse, urlsplit', 1)
text = text.replace('    from urllib.parse import urlparse as _urlparse\n    parts = _urlparse(url)', '    parts = urlparse(url)', 1)
text = text.replace('    parts = _urlparse(job_url)', '    parts = urlparse(job_url)', 1)
path.write_text(text, encoding='utf-8')
print('changed:', before != text)
