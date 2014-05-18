import logging
from pyengineio.util import generate_id

log = logging.getLogger(__name__)


class EngineIO(object):
    def __init__(self, options=None):
        if options is None:
            options = {}

        self.path = (options.get('path') or '/engine.io').rstrip('/')
        self.path += '/'

    def verify(self, query):
        pass

    def handle_request(self, handler, query):
        log.debug('handling request - query: %s', query)

        error_code = self.verify(query)

        if error_code:
            raise NotImplementedError()

        if query.get('sid'):
            log.debug('setting new request for existing client')
            raise NotImplementedError()
        else:
            self.handshake(handler, query['transport'])

        return self

    def handshake(self, handler, query, transport_name):
        id = generate_id()

        log.debug('handshaking client "%s"', id)

        try:
            transport = self.transports[transport_name](handler)

            # if transport_name == 'polling':
            #     transport.max_http_buffer_size = self.max_http_buffer_size

            transport.supports_binary = 'b64' not in query
        except Exception:
            raise NotImplementedError()

        socket = Socket(id, self, transport)
