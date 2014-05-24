import pyengineio_parser as parser

from pyemitter import Emitter


class Transport(Emitter):
    name = None
    upgrades_to = []
    supports_framing = False
    supports_upgrades = False

    def __init__(self, handle, query):
        """Transport constructor.

        :param handle: WSGI request handler
        :type handle: pyengineio.handler.Handler
        """
        self.ready_state = 'opening'
        self.should_close = None
        self.writable = False

        self.supports_binary = True

        self.sid = None

    def on_request(self, handle, query, method=None):
        """Called with incoming HTTP request.

        :param handle: WSGI request handler
        :type handle: pyengineio.handler.Handler

        :param method: HTTP request method
        :type method: str
        """
        raise NotImplementedError()

    def close(self, callback=None):
        """Closes the transport."""
        self.ready_state = 'closing'
        self.do_close(callback)

    def do_close(self, callback=None):
        raise NotImplementedError()

    def on_error(self, message, description=None):
        """Called with a transport error.

        :param message: Error message
        :type message: str

        :param description: Error description
        :type description: str
        """
        self.emit('error', Exception(message, description))

    def on_packet(self, packet):
        """Called with parsed out a packets from the data stream.

        :type packet: dict
        """
        self.emit('packet', packet)

    def on_data(self, data):
        """Called with the encoded packet data.

        :type data: str
        """
        self.on_packet(parser.decode_packet(data))

    def send(self, packets):
        """Writes a packet payload.

        :type packets: list of dict
        """
        raise NotImplementedError()

    def on_close(self, reason, description=None):
        """Called upon transport close."""
        self.ready_state = 'closed'
        self.emit('close', reason, description)
