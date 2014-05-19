import logging
from pyemitter import Emitter
from pyengineio.socket import Socket
from pyengineio.transports.polling import Polling
from pyengineio.transports.polling_xhr import XHR_Polling
from pyengineio.util import generate_id

log = logging.getLogger(__name__)


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

    def verify(self, query):
        pass

    def handle_request(self, handle, query):
        log.debug('handling request - query: %s', query)

        error_code = self.verify(query)

        if error_code:
            raise NotImplementedError()

        if query.get('sid'):
            log.debug('setting new request for existing client')
            self.clients[query['sid']].transport.on_request(handle)
        else:
            self.handshake(handle, query)

        return self

    def get_transport(self, query):
        name = query['transport']

        if name != 'polling':
            return self.transports[name]

        if 'j' in query:
            return self.transports['polling-jsonp']

        return self.transports['polling-xhr']

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
