import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import database_config

class DatabaseConfigTest(unittest.TestCase):
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
        with patch.dict(os.environ, {'DB_HOST': 'localhost', 'DB_PORT': 'wrong', 'DB_NAME': 'db',
                                      'DB_USER': 'user', 'DB_PASSWORD': 'password'}, clear=True), self.assertRaises(ValueError):
            database_config()
