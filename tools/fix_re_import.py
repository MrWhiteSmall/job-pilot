from pathlib import Path

path = Path(r'D:\DesktopCode\job-pilot\app.py')
text = path.read_text(encoding='utf-8')
if '\nimport re\n' not in text:
    text = text.replace('import random\n', 'import random\nimport re\n', 1)
path.write_text(text, encoding='utf-8')
print('ok', '\nimport re\n' in text)
