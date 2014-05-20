import pyengineio_parser as parser

from pyemitter import Emitter


class Transport(Emitter):
    name = None
    upgrades_to = []
    supports_framing = False
    supports_upgrades = False

    def __init__(self):
        self.ready_state = 'opening'
        self.should_close = None
        self.writable = False

        self.supports_binary = True

        self.sid = None

    def on_request(self, handle, method=None):
        raise NotImplementedError()

    def close(self, callback=None):
        raise NotImplementedError()

    def on_error(self, message, description=None):
        self.emit('error', Exception(message, description))

    def on_packet(self, packet):
        self.emit('packet', packet)

    def on_data(self, data):
        def decoded_packet(packet, index, count):
            self.on_packet(packet)

        parser.decode_payload(data, decoded_packet)

    def on_close(self):
        raise NotImplementedError()
