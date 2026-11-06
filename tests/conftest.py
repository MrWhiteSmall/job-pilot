"""Never let the test suite touch the live database.

Importing app.py builds a JobEngine, whose _init_db pauses any running
automation. Point JOB_PILOT_DB at a throwaway file before that import.
"""
import os
import tempfile

os.environ['JOB_PILOT_DB'] = os.path.join(tempfile.mkdtemp(prefix='jobpilot-test-'), 'test.sqlite3')
