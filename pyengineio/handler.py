from gevent.pywsgi import WSGIHandler
from geventwebsocket.handler import WebSocketHandler
import logging
import time
import traceback
import urlparse

log = logging.getLogger(__name__)


class Handler(WSGIHandler):
    logger = log

    def __init__(self, engine, *args, **kwargs):
        super(Handler, self).__init__(*args, **kwargs)

        self.engine = engine

    def initialize(self):
        # Setup
        self.time_start = time.time()

        self.code = None
        self.status = None
        self.headers_sent = False

        self.result = None
        self.response_use_chunked = False
        self.response_length = 0

    def handle_one_response(self):
        try:
            path = self.environ.get('PATH_INFO')

            if path != self.engine.path:
                return super(Handler, self).handle_one_response()

            self.initialize()

            request = Request.build(self)

            connection = self.headers.get('connection')
            upgrade = self.headers.get('upgrade')

            # Process websocket request
            if connection == 'Upgrade' and upgrade == 'websocket':
                return self.handle_websocket(request)

            return self.engine.handle_request(request)
        except Exception, ex:
            log.error('%s - %s' % (ex, traceback.format_exc()))
            raise ex

    def handle_websocket(self, request):
        # In case this is WebSocket request, switch to the WebSocketHandler
        # FIXME: fix this ugly class change
        old_class = self.__class__

        self.__class__ = WebSocketHandler
        self.prevent_wsgi_call = True  # thank you

        # TODO: any errors, treat them ??
        self.handle_one_response()  # does the Websocket dance before we continue

        # Switch back to the old class so references to this don't use the
        # incorrect class. Useful for debugging.
        self.__class__ = old_class

        return self.engine.handle_upgrade(request)


class Request(object):
    def __init__(self, handle):
        self.handle = handle

        self.method = None
        self.query = None
        self.headers = None

    @classmethod
    def build(cls, handle):
        o = Request(handle)

        o.method = handle.environ.get('REQUEST_METHOD')
        o.query = dict(urlparse.parse_qsl(handle.environ.get('QUERY_STRING'), keep_blank_values=True))
        o.headers = handle.headers

        return o
