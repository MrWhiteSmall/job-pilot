from pathlib import Path

path = Path(__file__).resolve().parent.parent / 'browser_adapter.py'
text = path.read_text(encoding='utf-8')
text = text.replace('page = context.new_page()', 'page = self._new_page()')
text = text.replace('detail = context.new_page()', 'detail = self._new_page()')
text = text.replace('self._sweep(keep=1, keep_detail=2)', 'self._sweep(keep=0)')
text = text.replace('self._sweep(keep=1)\n\n    def close', 'self._sweep(keep=0)\n\n    def close')
path.write_text(text, encoding='utf-8')
print(text.count('self._new_page()'), text.count('self._sweep('))
