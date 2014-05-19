from pyemitter import Emitter
import pyengineio_parser as parser


class Transport(Emitter):
    name = None
    supports_framing = False

    def __init__(self):
        self.ready_state = 'opening'
        self.should_close = None
        self.writable = False

        self.supports_binary = None

        self.sid = None

    def on_request(self, handle):
        raise NotImplementedError()

    def close(self, callback=None):
        raise NotImplementedError()

    def on_error(self, message, description=None):
        self.emit('error', Exception(message, description))

    def on_packet(self, packet):
        self.emit('packet', packet)

    def on_data(self, data):
        self.on_packet(parser.decode_packet(data))

    def on_close(self):
        raise NotImplementedError()
