from gevent.pywsgi import WSGIHandler
import time
import urlparse


class EngineIO_Handler(WSGIHandler):
    def __init__(self, engine, *args, **kwargs):
        super(EngineIO_Handler, self).__init__(*args, **kwargs)

        self.engine = engine

    def handle_one_response(self):
        path = self.environ.get('PATH_INFO')

        if path != self.engine.path:
            return super(EngineIO_Handler, self).handle_one_response()

        # Setup
        self.time_start = time.time()
        self.status = None
        self.headers_sent = False

        self.result = None
        self.response_use_chunked = False
        self.response_length = 0

        # Parse query
        query = dict(urlparse.parse_qsl(self.environ.get('QUERY_STRING'), keep_blank_values=True))

        # Process request
        return self.engine.handle_request(self, query)
