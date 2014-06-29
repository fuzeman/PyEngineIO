from pyengineio.transports.base import Transport
import pyengineio_parser as parser

from gevent.event import Event
import gevent
import logging

log = logging.getLogger(__name__)


class Polling(Transport):
    name = 'polling'
    upgrades_to = ['websocket', 'flashsocket']

    def __init__(self, request):
        super(Polling, self).__init__(request)

        self.poll_handle = None
        self.poll_lock = None

        self.data_handle = None

    def on_request(self, request):
        if request.method == 'GET':
            self.on_poll_request(request)
        elif request.method == 'POST':
            self.on_data_request(request)
        else:
            log.warn('Unknown polling request')

    def on_poll_request(self, request):
        if self.poll_handle:
            self.on_error('overlap from client')

            self.poll_handle.start_response('500', [
                ('Connection', 'close')
            ])
            return

        self.poll_handle = request.handle
        self.poll_lock = Event()

        self.writable = True
        self.ready_state = 'open'

        self.emit('drain')

        # if we're still writable but had a pending close, trigger an empty send
        if self.writable and self.should_close:
            log.debug('triggering empty send to append close packet')
            self.send([{'type': 'noop'}])

        # Wait until we are ready to send something
        gevent.wait([self.poll_lock])

    def on_data_request(self, request):
        if self.data_handle:
            self.on_error('data request overlap from client')

            self.data_handle.start_response('500', [
                ('Connection', 'close')
            ])
            return

        self.data_handle = request.handle

        content_length = request.handle.headers['content-length']

        # Read data from input stream
        stream = request.handle.environ.get('wsgi.input')

        data = stream.read(content_length)

        if request.handle.headers['content-type'] == 'application/octet-stream':
            data = bytearray(data)

        # Write response
        self.data_handle.start_response('200 OK', [
            ('Content-Length', '2'),
            # text/html is required instead of text/plain to avoid an
            # unwanted download dialog on certain user-agents (GH-43)
            ('Content-Type', 'text/html'),
            ('Connection', 'close')
        ])

        self.data_handle.write('ok')

        # Received data from client
        self.on_data(data)

        # Cleanup
        self.data_handle = None

    def on_data(self, data):
        def decoded_packet(packet, index, count):
            if packet.get('type') == 'close':
                self.on_close('received "close" packet')
                return

            self.on_packet(packet)

        parser.decode_payload(data, decoded_packet)

    def send(self, packets):
        log.debug('sending packets: %s', packets)

        if self.should_close:
            log.debug('appending close packet to payload')
            packets.append({'type': 'close'})

            self.should_close()
            self.should_close = None

        parser.encode_payload(packets, lambda data: self.write(data), self.supports_binary)

    def write(self, data):
        self.do_write(data)

        # Cleanup
        self.poll_handle = None
        self.poll_lock.set()

        self.writable = False

    def do_write(self, data):
        raise NotImplementedError()
