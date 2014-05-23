from pyengineio.transports.base import Transport
import pyengineio_parser as parser

from geventwebsocket import WebSocketError
import gevent
import logging

log = logging.getLogger(__name__)


class WebSocket(Transport):
    name = 'websocket'
    supports_framing = True
    supports_upgrades = True

    def __init__(self, handle):
        super(WebSocket, self).__init__(handle)

        self.socket = handle.environ.get('wsgi.websocket')
        self.writable = True

        self.receive_job = gevent.spawn(self.receive)

    def on_request(self, handle, method=None):
        gevent.joinall([self.receive_job])

    def receive(self):
        while not self.socket.closed:
            try:
                data = self.socket.read_message()
            except Exception, ex:
                return self.emit('error', 'read error %s' % ex)

            if data is None:
                break

            self.on_data(data)

    def send(self, packets):
        for packet in packets:
            parser.encode_packet(packet, self.write, self.supports_binary)

    def write(self, data):
        self.writable = False

        try:
            self.socket.send(data)
        except (WebSocketError, TypeError), ex:
            # We can't send a message on the socket
            # it is dead, let the other sockets know
            return self.emit('error', 'write error %s' % ex)

        self.writable = True
        self.emit('drain')
