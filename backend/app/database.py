"""Configuración compartida para PostgreSQL local."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / '.env', override=False)


def database_config(prefix=None):
    if prefix == 'EVENTS':
        names = ('HOST', 'PORT', 'NAME', 'USER', 'PASSWORD')
        values = {key: os.environ.get('EVENTS_DB_' + key) for key in names}
        missing = ['EVENTS_DB_' + key for key in names if not values[key]]
        if missing:
            raise ValueError('Faltan variables de la base de eventos: ' + ', '.join(missing))
        try:
            port = int(values['PORT'])
        except ValueError as exc:
            raise ValueError('EVENTS_DB_PORT debe ser un número válido') from exc
        if not 1 <= port <= 65535:
            raise ValueError('EVENTS_DB_PORT debe estar entre 1 y 65535')
        return {'host': values['HOST'], 'port': port, 'dbname': values['NAME'],
                'user': values['USER'], 'password': values['PASSWORD'], 'connect_timeout': 5}
    # No mezclar credenciales de Neon con las de una base local.
    aliases = {'DB_HOST': 'PGHOST', 'DB_PORT': 'PGPORT', 'DB_NAME': 'PGDATABASE',
               'DB_USER': 'PGUSER', 'DB_PASSWORD': 'PGPASSWORD'}
    prefer_pg = os.environ.get('DB_DATA_SOURCE') == 'armonizados'
    use_pg = bool(os.environ.get('PGHOST')) and (prefer_pg or not os.environ.get('DB_HOST'))
    values = {key: os.environ.get(alias if use_pg else key) for key, alias in aliases.items()}
    if use_pg:
        values['DB_PORT'] = values['DB_PORT'] or '5432'
    if not values['DB_PORT'] and os.environ.get('PGHOST'):
        values['DB_PORT'] = '5432'
    required = ('DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD')
    missing = [name for name in required if not values[name]]
    if missing:
        raise ValueError('Faltan variables de PostgreSQL: ' + ', '.join(aliases[name] if use_pg else name for name in missing))
    try:
        port = int(values['DB_PORT'])
    except ValueError as exc:
        raise ValueError('DB_PORT debe ser un número válido') from exc
    if not 1 <= port <= 65535:
        raise ValueError('DB_PORT debe estar entre 1 y 65535')
    config = {'host': values['DB_HOST'], 'port': port, 'dbname': values['DB_NAME'],
              'user': values['DB_USER'], 'password': values['DB_PASSWORD'], 'connect_timeout': 5}
    sslmode = os.environ.get('PGSSLMODE' if use_pg else 'DB_SSLMODE')
    if sslmode:
        if sslmode not in ('disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'):
            raise ValueError('DB_SSLMODE no es válido')
        config['sslmode'] = sslmode
    binding = os.environ.get('PGCHANNELBINDING') if use_pg else None
    if binding:
        if binding not in ('disable', 'prefer', 'require'):
            raise ValueError('PGCHANNELBINDING no es válido')
        config['channel_binding'] = binding
    return config
