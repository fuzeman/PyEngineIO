from pyengineio.socket import Socket
from pyengineio.transports.polling_xhr import XHR_Polling
from pyengineio.util import generate_id

from pyemitter import Emitter
import json
import logging

log = logging.getLogger(__name__)


class Errors(object):
    UNKNOWN_TRANSPORT = 0
    UNKNOWN_SID = 1

    BAD_HANDSHAKE_METHOD = 2
    BAD_REQUEST = 3

    MESSAGES = {
        UNKNOWN_TRANSPORT: 'Transport unknown',
        UNKNOWN_SID: 'Session ID unknown',
        BAD_HANDSHAKE_METHOD: 'Bad handshake method',
        BAD_REQUEST: 'Bad request'
    }


class EngineIO(Emitter):
    transports = {
        'polling-xhr': XHR_Polling
    }

    def __init__(self, options=None):
        if options is None:
            options = {}

        self.path = (options.get('path') or '/engine.io').rstrip('/')
        self.path += '/'

        self.clients = {}
        self.clients_count = 0

        self.ping_timeout = options.get('ping_timeout', 60000)
        self.ping_interval = options.get('ping_interval', 25000)

        self.allow_upgrades = options.get('allow_upgrades', True)

    def upgrades(self, transport):
        if not self.allow_upgrades:
            return []

        return self.transports[transport].upgrades_to or []

    def verify(self, method, query, upgrade):
        # transport check
        transport = self.get_transport_name(query)

        if transport not in self.transports:
            log.debug('unknown transport "%s"', transport)
            return Errors.UNKNOWN_TRANSPORT

        # sid check
        sid = query.get('sid')

        if sid is not None:
            if sid not in self.clients:
                return Errors.UNKNOWN_SID

            if not upgrade and self.clients[sid].transport.name != transport:
                log.debug('bad request: unexpected transport without upgrade')
                return Errors.BAD_REQUEST
        else:
            if method != 'GET':
                return Errors.BAD_HANDSHAKE_METHOD

        return None

    def handle_request(self, handle, query):
        log.debug('handling request - query: %s', query)

        method = handle.environ.get('REQUEST_METHOD')

        error_code = self.verify(method, query, False)

        if error_code is not None:
            self.send_error(handle, error_code)
            return self

        if query.get('sid'):
            log.debug('setting new request for existing client')
            self.clients[query['sid']].transport.on_request(handle, method)
        else:
            self.handshake(handle, query)

        return self

    @staticmethod
    def get_transport_name(query):
        if not query or 'transport' not in query:
            return None

        name = query['transport']

        if name != 'polling':
            return name

        if 'j' in query:
            return 'polling-jsonp'

        return 'polling-xhr'

    def get_transport(self, query):
        name = self.get_transport_name(query)
        return self.transports.get(name)

    def handshake(self, handle, query):
        sid = generate_id()

        log.debug('handshaking client "%s"', sid)

        try:
            transport = self.get_transport(query)()

            # if transport_name == 'polling':
            #     transport.max_http_buffer_size = self.max_http_buffer_size

            transport.supports_binary = 'b64' not in query
        except Exception, ex:
            raise ex

        socket = Socket(self, sid, transport)

        # if self.cookie:
        #     handler.headers['Set-Cookie'] = self.cookie + '=' + sid

        transport.on_request(handle)

        self.clients[sid] = socket
        self.clients_count += 1

        @socket.once('close')
        def on_close():
            del self.clients[sid]
            self.clients_count -= 1

        self.emit('connection', socket)

    @staticmethod
    def send_error(handle, code):
        handle.start_response('400 Bad Request', [
            ('Content-Type', 'application/json'),
            ('Connection', 'close')
        ])

        handle.write(json.dumps({
            'code': code,
            'message': Errors.MESSAGES.get(code)
        }))
