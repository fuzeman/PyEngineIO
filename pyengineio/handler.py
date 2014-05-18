from gevent.wsgi import WSGIHandler
import urlparse


class EngineIO_Handler(WSGIHandler):
    def __init__(self, engine, *args, **kwargs):
        super(EngineIO_Handler, self).__init__(*args, **kwargs)

        self.engine = engine

    def handle_one_response(self):
        path = self.environ.get('PATH_INFO')

        if path != self.engine.path:
            return super(EngineIO_Handler, self).handle_one_response()

        query = dict(urlparse.parse_qsl(self.environ.get('QUERY_STRING'), keep_blank_values=True))
        print query

        return self.engine.handle_request(self, query)
