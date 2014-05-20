from pyengineio.transports.base import Transport
import pyengineio_parser as parser

import logging

log = logging.getLogger(__name__)


class Polling(Transport):
    name = 'polling'
    upgrades_to = ['websocket', 'flashsocket']

    def __init__(self):
        super(Polling, self).__init__()

        self.poll_handle = None
        self.data_handle = None

    def on_request(self, handle, method=None):
        if method is None:
            method = handle.environ.get('REQUEST_METHOD')

        if method == 'GET':
            self.on_poll_request(handle)
        elif method == 'POST':
            self.on_data_request(handle)
        else:
            raise NotImplementedError()

    def on_poll_request(self, handle):
        if self.poll_handle:
            self.on_error('overlap from client')

            self.poll_handle.start_response('500', [
                ('Connection', 'close')
            ])
            return

        log.debug('setting handle')

        self.poll_handle = handle

        # TODO onClose, cleanup

        self.writable = True
        self.emit('drain')

        # if we're still writable but had a pending close, trigger an empty send
        if self.writable and self.should_close:
            log.debug('triggering empty send to append close packet')
            self.send([{'type': 'noop'}])

    def on_data_request(self, handle):
        if self.data_handle:
            self.on_error('data request overlap from client')

            self.data_handle.start_response('500', [
                ('Connection', 'close')
            ])
            return

        self.data_handle = handle

        content_length = handle.headers['content-length']

        # Read data from input stream
        stream = handle.environ.get('wsgi.input')

        data = stream.read(content_length)

        if handle.headers['content-type'] == 'application/octet-stream':
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
        log.debug('received %s', repr(data))

        self.on_data(data)

        # Cleanup
        self.data_handle = None

    def send(self, packets):
        if self.should_close:
            log.debug('appending close packet to payload')
            packets.append({'type': 'close'})

            self.should_close()
            self.should_close = None

        parser.encode_payload(packets, lambda data: self.write(data), self.supports_binary)

    def write(self, data):
        log.debug('writing %s', repr(data))
        self.do_write(data)

        # Cleanup
        self.poll_handle = None
        self.writable = False

    def do_write(self, data):
        raise NotImplementedError()
