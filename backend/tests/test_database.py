import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import database_config

class DatabaseConfigTest(unittest.TestCase):
    def test_separate_events_database(self):
        variables = {'EVENTS_DB_HOST': '127.0.0.1', 'EVENTS_DB_PORT': '5432', 'EVENTS_DB_NAME': 'econovas',
                     'EVENTS_DB_USER': 'postgres', 'EVENTS_DB_PASSWORD': 'secret'}
        with patch.dict(os.environ, variables, clear=True):
            self.assertEqual(database_config('EVENTS')['dbname'], 'econovas')
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            database_config('EVENTS')
    def test_neon_pg_variables_and_default_port(self):
        variables = {'PGHOST': 'example.neon.tech', 'PGDATABASE': 'db', 'PGUSER': 'user',
                     'PGPASSWORD': 'secret', 'PGSSLMODE': 'require', 'PGCHANNELBINDING': 'require'}
        with patch.dict(os.environ, variables, clear=True):
            config = database_config()
        self.assertEqual(config['port'], 5432)
        self.assertEqual(config['sslmode'], 'require')
        self.assertEqual(config['channel_binding'], 'require')

    def test_separate_variables(self):
        variables = {'DB_HOST': 'localhost', 'DB_PORT': '5432', 'DB_NAME': 'brinco',
                     'DB_USER': 'user', 'DB_PASSWORD': 'secret'}
        with patch.dict(os.environ, variables, clear=True):
            config = database_config()
        self.assertEqual(config['dbname'], 'brinco')
        self.assertEqual(config['port'], 5432)
        self.assertEqual(config['password'], 'secret')

    def test_missing_and_invalid_port(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            database_config()

    def test_neon_sslmode(self):
        variables = {'DB_HOST': 'example.neon.tech', 'DB_PORT': '5432', 'DB_NAME': 'db',
                     'DB_USER': 'user', 'DB_PASSWORD': 'secret', 'DB_SSLMODE': 'require'}
        with patch.dict(os.environ, variables, clear=True):
            self.assertEqual(database_config()['sslmode'], 'require')
        with patch.dict(os.environ, {**variables, 'DB_SSLMODE': 'bad'}, clear=True):
            with self.assertRaises(ValueError):
                database_config()
        with patch.dict(os.environ, {'DB_HOST': 'localhost', 'DB_PORT': 'wrong', 'DB_NAME': 'db',
                                      'DB_USER': 'user', 'DB_PASSWORD': 'password'}, clear=True), self.assertRaises(ValueError):
            database_config()
