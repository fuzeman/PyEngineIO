from pyengineio.transports.base import Transport
import pyengineio_parser as parser

from geventwebsocket import WebSocketError
import gevent
import logging
import socket

log = logging.getLogger(__name__)


class WebSocket(Transport):
    name = 'websocket'
    supports_framing = True
    supports_upgrades = True

    def __init__(self, handle, query):
        super(WebSocket, self).__init__(handle, query)

        self.socket = handle.environ.get('wsgi.websocket')
        self.socket.current_app.on_close = lambda reason, *args: self.on_close(reason)

        self.writable = True
        self.ready_state = 'open'

        self.receive_job = gevent.spawn(self.receive)

    def on_request(self, handle, query, method=None):
        gevent.joinall([self.receive_job])

    def receive(self):
        while not self.socket.closed:
            try:
                data = self.socket.read_message()
            except socket.error, ex:
                return self.on_close(*ex)
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

    def do_close(self, callback=None):
        log.debug('closing')

        self.socket.close()

        if callback:
            callback()
