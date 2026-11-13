"""Configuración compartida para PostgreSQL local."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / '.env', override=False)


def database_config():
    required = ('DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD')
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ValueError('Faltan variables de PostgreSQL: ' + ', '.join(missing))
    try:
        port = int(os.environ['DB_PORT'])
    except ValueError as exc:
        raise ValueError('DB_PORT debe ser un número válido') from exc
    if not 1 <= port <= 65535:
        raise ValueError('DB_PORT debe estar entre 1 y 65535')
    return {'host': os.environ['DB_HOST'], 'port': port, 'dbname': os.environ['DB_NAME'],
            'user': os.environ['DB_USER'], 'password': os.environ['DB_PASSWORD'], 'connect_timeout': 5}
