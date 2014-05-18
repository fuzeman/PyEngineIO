class Middleware(object):
    def __init__(self, app, server, path):
        self.app = app

    def __call__(self, environ, start_response):
        return self.app(environ, start_response)
