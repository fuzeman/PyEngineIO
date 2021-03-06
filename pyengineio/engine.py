from pyengineio.errors import Errors
from pyengineio.socket import Socket
from pyengineio.transports import TRANSPORTS
from pyengineio.util import generate_id

from pyemitter import Emitter
import json
import logging

log = logging.getLogger(__name__)


class Engine(Emitter):
    transports = TRANSPORTS

    def __init__(self, options=None):
        """Engine constructor.

        :param options: Engine configuration options
        :type options: dict
        """
        if options is None:
            options = {}

        self.path = (options.get('path') or '/engine.io').rstrip('/')
        self.path += '/'

        self.clients = {}
        self.clients_count = 0

        self.ping_timeout = options.get('ping_timeout', 60000)
        self.ping_interval = options.get('ping_interval', 25000)

        self.upgrade_timeout = options.get('upgrade_timeout', 10000)

        self.allow_upgrades = options.get('allow_upgrades', True)
        self.allow_request = options.get('allow_request')

    def upgrades(self, transport):
        """Returns a list of available transports for upgrade given a certain transport.

        :param transport: Transport name
        :type transport: str

        :rtype: list of str
        """
        if not self.allow_upgrades:
            return []

        return self.transports[transport].upgrades_to or []

    def verify(self, request, upgrade):
        """Verifies a request.

        :param request: HTTP request
        :type request: pyengineio.handler.Request

        :param upgrade: Is this an upgrade request?
        :type upgrade: bool

        :return: Is the request valid?
        :rtype: bool
        """
        # transport check
        transport = self.get_transport_name(request.query)

        if transport not in self.transports:
            log.debug('unknown transport "%s"', transport)
            return False, Errors.UNKNOWN_TRANSPORT

        # sid check
        sid = request.query.get('sid')

        if sid is not None:
            if sid not in self.clients:
                return False, Errors.UNKNOWN_SID

            if not upgrade and self.clients[sid].transport.name != transport:
                log.debug('bad request: unexpected transport without upgrade')
                return False, Errors.BAD_REQUEST
        else:
            if request.method != 'GET':
                return False, Errors.BAD_HANDSHAKE_METHOD

            if self.allow_request and not self.allow_request(request, upgrade):
                return False, Errors.REFUSED_HANDSHAKE

        return True, None

    def close(self):
        """Closes all clients."""
        log.debug('closing all open clients')

        for client in self.clients:
            client.close()

        return self

    def handle_request(self, request):
        """Handles a WSGI request

        :param request: HTTP request
        :type request: pyengineio.handler.Request
        """
        log.debug('handling request - request: %s', request)

        # Verify request
        success, error = self.verify(request, False)

        if not success:
            self.send_error(request, error)
            return self

        # Handle request
        sid = request.query.get('sid')

        if not sid:
            # Handshake new client
            return self.handshake(request)

        log.debug('setting new request for existing client')
        self.clients[sid].transport.on_request(request)

        request.handle.log_request()

    @staticmethod
    def send_error(request, code):
        """Returns an error for an HTTP request

        :param request: HTTP Request
        :type request: pyengineio.handler.Request

        :param code: Error code
        :type code: int
        """
        if not request or not request.handle:
            log.warn('invalid handle')
            return

        request.handle.start_response('400 Bad Request', [
            ('Content-Type', 'application/json'),
            ('Connection', 'close')
        ])

        request.handle.write(json.dumps({
            'code': code,
            'message': Errors.MESSAGES.get(code)
        }))

    def handshake(self, request):
        """Handshakes a new client.

        :param request: HTTP Request
        :type request: pyengineio.handler.Request

        :param query: HTTP request query
        :type query: dict
        """
        sid = generate_id()

        log.debug('handshaking client "%s"', sid)

        transport = self.get_transport(request.query)(request)

        # if transport_name == 'polling':
        #     transport.max_http_buffer_size = self.max_http_buffer_size

        transport.supports_binary = 'b64' not in request.query

        socket = Socket(self, sid, transport, request)

        # if self.cookie:
        #     handler.headers['Set-Cookie'] = self.cookie + '=' + sid

        transport.on_request(request)

        self.clients[sid] = socket
        self.clients_count += 1

        @socket.once('close')
        def on_close(reason, description=None):
            del self.clients[sid]
            self.clients_count -= 1

        self.emit('connection', socket)

    def handle_upgrade(self, request):
        """Handles a client upgrade request

        :param request: HTTP Request
        :type request: pyengineio.handler.Request
        """
        log.debug('handling upgrade - request: %s', request)

        # Verify request
        success, error = self.verify(request, True)

        if not success:
            self.send_error(request, error)
            return self

        # Handle upgrade request
        transport = self.get_transport(request.query)

        if not transport.supports_upgrades:
            log.debug('transport doesnt support upgrading')
            self.send_error(request, Errors.UNSUPPORTED_UPGRADE)
            return

        sid = request.query.get('sid')

        if not sid:
            # Handshake new client
            return self.handshake(request)

        # Verify upgrade request
        if sid not in self.clients:
            log.debug('upgrade attempt for closed client')
            return

        if self.clients[sid].upgraded:
            log.debug('transport has already been upgraded')
            self.send_error(request, Errors.ALREADY_UPGRADED)
            return

        # Upgrade transport
        log.debug('upgrading existing transport')
        transport = transport(request)

        # Set binary mode
        if request.query.get('b64'):
            transport.supports_binary = False
        else:
            transport.supports_binary = True

        # Start upgrade
        self.clients[sid].maybe_upgrade(transport)

        transport.on_request(request)

    @staticmethod
    def get_transport_name(query):
        """Determine transport name from query

        :param query: HTTP request query
        :type query: dict

        :return: Transport name
        :rtype: str
        """
        if not query or 'transport' not in query:
            return None

        name = query['transport']

        if name != 'polling':
            return name

        if 'j' in query:
            return 'polling-jsonp'

        return 'polling-xhr'

    def get_transport(self, query):
        """Determine transport class from query

        :param query: HTTP request query
        :type query: dict

        :return: Transport class
        :rtype: class
        """
        return self.transports.get(
            self.get_transport_name(query)
        )
