"""Experiment: does attaching Playwright kill the user's Chrome, and on detach?"""
import json
import os
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

port = sys.argv[1]
base = f'http://127.0.0.1:{port}'


def alive():
    try:
        with urllib.request.urlopen(base + '/json/version', timeout=2) as r:
            return r.status
    except Exception as exc:
        return f'dead: {exc}'


print('before_attach', alive(), flush=True)
pw = sync_playwright().start()
conn = pw.chromium.connect_over_cdp(base, timeout=15000)
print('after_connect', alive(), flush=True)
for context in conn.contexts:
    for page in context.pages:
        try:
            print('page', page.url, flush=True)
        except Exception as exc:
            print('page_error', exc, flush=True)
time.sleep(2)
print('after_2s', alive(), flush=True)
pw.stop()
time.sleep(1)
print('after_stop', alive(), flush=True)
os._exit(0)
