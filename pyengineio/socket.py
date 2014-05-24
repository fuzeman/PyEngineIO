from pyemitter import Emitter
from threading import Timer
import json
import logging

log = logging.getLogger(__name__)


class Socket(Emitter):
    def __init__(self, engine, sid, transport):
        """Socket constructor

        :param engine: Engine instance
        :type engine: pyengineio.engine.Engine

        :param sid: Client SID
        :type sid: str

        :param transport: Client transport
        :type transport: pyengineio.transports.base.Transport
        """
        self.engine = engine
        self.sid = sid
        self.transport = None

        self.upgraded = False
        self.ready_state = 'opening'

        self.write_buffer = []
        self.write_callbacks = []
        self.response_callbacks = []

        self.check_interval_timer = None
        self.upgrade_timeout_timer = None
        self.ping_timeout_timer = None

        self.set_transport(transport)
        self.on_open()

    def on_open(self):
        """Called upon transport considered open."""
        self.ready_state = 'open'

        # sends an 'open' packet
        self.transport.sid = self.sid

        self.send_packet('open', json.dumps({
            'sid': self.sid,
            'upgrades': self.get_available_upgrades(),

            'pingInterval': self.engine.ping_interval,
            'pingTimeout': self.engine.ping_timeout
        }))

        self.emit('open')
        self.set_ping_timeout()

    def on_packet(self, packet):
        """Called upon transport packet.

        :param packet: decoded packet
        :type packet: dict
        """
        if self.ready_state != 'open':
            log.debug('packet received with closed socket')
            return

        log.debug('Received via "%s" transport - packet: %s', self.transport.name, packet)

        self.emit('packet', packet)

        # Reset ping timeout on any packet, incoming data is a good sign of
        # other side's liveness
        self.set_ping_timeout()

        p_type = packet.get('type')

        if p_type == 'ping':
            log.debug('got ping')

            # Respond with pong
            self.send_packet('pong')

            self.emit('heartbeat')
            return

        if p_type == 'error':
            self.on_close('parse error')
            return

        if p_type == 'message':
            data = packet.get('data')

            self.emit('data', data)
            self.emit('message', data)
            return

        log.warn('Received unknown packet with type "%s"', p_type)

    def on_error(self, error):
        """Called upon transport error."""
        log.debug('transport error')
        self.on_close('transport error', error)

    def set_ping_timeout(self):
        """Sets and resets ping timeout timer based on client pings."""
        if self.ping_timeout_timer:
            self.ping_timeout_timer.cancel()

        def on_ping_timeout():
            self.on_close('ping timeout')

        timeout = self.engine.ping_interval + self.engine.ping_timeout

        self.ping_timeout_timer = Timer(timeout / 1000, on_ping_timeout)
        self.ping_timeout_timer.start()

    def set_transport(self, transport):
        """Attaches handlers for the given transport.

        :param transport: Transport
        :type transport: pyengineio.transports.base.Transport
        """
        self.transport = transport

        transport.once('error', self.on_error)\
                 .once('close', self.on_close)\
                 .on('packet', self.on_packet)\
                 .on('drain', lambda: self.flush())

    def maybe_upgrade(self, transport):
        """Upgrades socket to the given transport

        :param transport: Transport
        :type transport: pyengineio.transports.base.Transport
        """
        log.debug(
            'might upgrade socket transport from "%s" to "%s"',
            self.transport.name, transport.name
        )

        # TODO upgrade timeout

        def polling_close():
            if self.transport.name != 'polling' or not self.transport.writable:
                return

            log.debug('writing a noop packet to polling transport for fast upgrade')
            self.transport.send([{'type': 'noop'}])

        @transport.on('packet')
        def on_packet(packet):
            p_type = packet.get('type')
            p_data = packet.get('data')

            if p_type == 'ping' and p_data == 'probe':
                transport.send([{'type': 'pong', 'data': 'probe'}])
                polling_close()
            elif p_type == 'upgrade' and self.ready_state == 'open':
                log.debug('got upgrade packet - upgrading')
                self.upgraded = True

                self.clear_transport()

                self.set_transport(transport)
                self.emit('upgrade', transport)

                self.set_ping_timeout()
                self.flush()

                # TODO clearTimeout(self.upgradeTimeoutTimer);
                transport.off('packet', on_packet)
            else:
                transport.close()

    def clear_transport(self):
        """Clears listeners and timers associated with current transport."""
        self.transport.off('error')

        self.ping_timeout_timer.cancel()
        self.ping_timeout_timer = None

    def on_close(self, reason, description=None):
        """Called upon transport considered closed."""
        if self.ready_state == 'closed':
            return

        self.clear_transport()

        # reset buffers
        self.write_buffer = []
        self.write_callbacks = []
        self.response_callbacks = []

        self.ready_state = 'closed'
        self.emit('close', reason, description)

    def setup_send_callback(self):
        """Setup and manage send callback"""
        raise NotImplementedError()

    def write(self, data, callback=None):
        """Sends a message packet.

        :param data: Message data
        :type data: str

        :param callback: Response callback
        :type callback: function
        """
        self.send_packet('message', data, callback)
        return self

    # Alias for write()
    send = write

    def send_packet(self, type, data=None, callback=None):
        """ Sends a packet.

        :param type: Packet type
        :type type: str

        :param data: Packet data
        :type data: str

        :param callback: Response callback
        :type callback: function
        """
        if self.ready_state == 'closing':
            return

        log.debug('sending packet "%s" (%s)', type, data)

        packet = {'type': type}

        if data:
            packet['data'] = data

        # exports packetCreate event
        self.emit('packetCreate', packet)

        self.write_buffer.append(packet)

        # add send callback to object
        self.response_callbacks.append(callback)

        self.flush()

    def flush(self):
        """Attempts to flush the packet buffer."""
        if self.ready_state == 'closed' or not self.transport.writable:
            return

        if not self.write_buffer:
            return

        log.debug('flushing buffer to transport')

        self.emit('flush', self.write_buffer)
        self.engine.emit('flush', self, self.write_buffer)

        wbuf = self.write_buffer
        self.write_buffer = []

        if not self.transport.supports_framing:
            self.write_callbacks.append(self.write_callbacks)
        else:
            # TODO check this is correct
            self.write_callbacks.extend(self.write_callbacks)

        self.write_callbacks = []

        log.debug('Sending via "%s" transport - packets: %s', self.transport.name, wbuf)
        self.transport.send(wbuf)

        self.emit('drain')
        self.engine.emit('drain', self)

    def get_available_upgrades(self):
        """Get available upgrades for this socket.

        :return: list of available upgrades
        :rtype: list of str
        """
        all_upgrades = self.engine.upgrades(self.transport.name)
        available_upgrades = []

        for upgrade in all_upgrades:
            if upgrade in self.engine.transports:
                available_upgrades.append(upgrade)

        return available_upgrades

    def close(self):
        """Closes the socket and underlying transport."""
        raise NotImplementedError()
