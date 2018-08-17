# -*- coding:utf-8 -*-

import numbers
import exceptions
from url import _parse_url

try:
    import redis
except ImportError:
    redis = None

DEFAULT_PORT = 6379
DEFAULT_DB = 0

class RedisChannel(object):

    _pool = None

    attrs = (
        ('hostname', None),
        ('port', None),
        ('password', None),
        ('max_connections', None),
        ('socket_timeout', None),
        ('socket_connect_timeout', None),
        ('socket_keepalive', bool),
        ('socket_keepalive_options', bool),
        ('auto_delete', bool),
    )

    max_connections = 10
    virtual_host = '/'

    def __init__(self, *args, **kwargs):
        self.args = args or []
        self.kwargs = dict(**kwargs or {})
        for name, type_ in self.attrs:
            value = kwargs.get(name)
            if value is not None:
                setattr(self, name, (type_ or (lambda v: v))(value))
            else:
                try:
                    getattr(self, name)
                except AttributeError:
                    setattr(self, name, None)

    @property
    def pool(self):
        if self._pool is None:
            self._pool = self._get_pool()
        return self._pool

    @property
    def client(self):
        return self._create_client()

    def _create_client(self):
        return redis.Redis(connection_pool=self.pool)

    def _get_pool(self):
        params = self._connparams()
        return redis.ConnectionPool(**params)

    def _connparams(self, async=False, _r210_options=(
        'socket_connect_timeout', 'socket_keepalive',
        'socket_keepalive_options')):

        connparams = {
            'host': self.hostname or '127.0.0.1',
            'port': self.port or DEFAULT_PORT,
            'virtual_host': self.virtual_host,
            'password': self.password,
            'max_connections': self.max_connections,
            'socket_timeout': self.socket_timeout,
            'socket_connect_timeout': self.socket_connect_timeout,
            'socket_keepalive': self.socket_keepalive,
            'socket_keepalive_options': self.socket_keepalive_options,
        }
        if redis.VERSION < (2, 10):
            for param in _r210_options:
                val = connparams.pop(param, None)
                if val is not None:
                    raise exceptions.VersionMismatch(
                        'redis: {0!r} requires redis 2.10.0 or higher'.format(
                        param))
        host = connparams['host']
        if '://' in host:
            scheme, _, _, _, password, path, query = _parse_url(host)
            if scheme == 'socket':
                connparams = self._filter_tcp_connparams(**connparams)
                connparams.update({
                    'connection_class': redis.UnixDomainSocketConnection,
                    'path': '/' + path,
                    'password': password}, **query)
                connparams.pop('socket_connect_timeout', None)
                connparams.pop('socket_keepalive', None)
                connparams.pop('socket_keepalive_options', None)

            connparams.pop('host', None)
            connparams.pop('port', None)
        connparams['db'] = self._prepare_virtual_host(
            connparams.pop('virtual_host', None))

        connparams['connection_class'] = connparams.get('connection_class') or redis.Connection
        return connparams

    def _filter_tcp_connparams(self, socket_keepalive=None,
                               socket_keepalive_options=None, **params):
        return params

    def _prepare_virtual_host(self, vhost):
        if not isinstance(vhost, numbers.Integral):
            if not vhost or vhost == '/':
                vhost = DEFAULT_DB
            elif vhost.startswith('/'):
                vhost = vhost[1:]
            try:
                vhost = int(vhost)
            except ValueError:
                raise ValueError(
                    'Database is int between 0 and limit - 1, not {0}'.format(
                        vhost,
                    ))
        return vhost
