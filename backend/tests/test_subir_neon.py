import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).resolve().parents[2] / 'data-pipeline' / 'subir_observaciones_neon.py'
spec = importlib.util.spec_from_file_location('subir_observaciones_neon', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class UploadConfigTest(unittest.TestCase):
    def test_local_and_neon_are_selected_independently(self):
        variables = {'DB_HOST': '127.0.0.1', 'DB_PORT': '5432', 'DB_NAME': 'local',
                     'DB_USER': 'local_user', 'DB_PASSWORD': 'local_secret',
                     'PGHOST': 'neon.example', 'PGDATABASE': 'remote', 'PGUSER': 'remote_user',
                     'PGPASSWORD': 'remote_secret', 'PGSSLMODE': 'require', 'PGCHANNELBINDING': 'require'}
        with patch.dict(os.environ, variables, clear=True):
            local = module.local_settings()
            remote = module.connection_settings()
        self.assertEqual((local['host'], local['dbname'], local['sslmode']), ('127.0.0.1', 'local', 'prefer'))
        self.assertEqual((remote['host'], remote['dbname'], remote['sslmode']), ('neon.example', 'remote', 'require'))


if __name__ == '__main__':
    unittest.main()
