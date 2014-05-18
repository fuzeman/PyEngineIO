from pyengineio.middleware import Middleware
from pyengineio.server import Server


def listen(port, options):
    pass


def attach(app, options=None):
    options = options or {}

    server = Server(options)
    path = (options.get('path') or '/engine.io').rstrip('/')

    # normalize path
    path += '/'

    app.wsgi_app = Middleware(app.wsgi_app, server, path)

    return server
