from pyemitter import Emitter
import json
import logging

log = logging.getLogger(__name__)


class Socket(Emitter):
    def __init__(self, engine, sid, transport):
        self.engine = engine
        self.sid = sid
        self.upgraded = False
        self.ready_state = 'opening'

        self.write_buffer = []
        self.write_callbacks = []
        self.response_callbacks = []

        self.transport = None
        self.set_transport(transport)

        self.on_open()

    def on_open(self):
        self.ready_state = 'open'

        # sends an 'open' packet
        self.transport.sid = self.sid

        self.send_packet('open', json.dumps({
            'sid': self.sid,
            'upgrades': self.get_available_upgrades(),

            'ping_interval': self.engine.ping_interval,
            'ping_timeout': self.engine.ping_timeout
        }))

        self.emit('open')
        self.set_ping_timeout()

    def on_packet(self, packet):
        raise NotImplementedError()

    def on_error(self, error):
        raise NotImplementedError()

    def set_ping_timeout(self):
        raise NotImplementedError()

    def set_transport(self, transport):
        self.transport = transport

        transport.once('error', self.on_error)\
                 .once('close', self.on_close)\
                 .on('packet', self.on_packet)\
                 .on('drain', lambda: self.flush())

    def maybe_upgrade(self, transport):
        raise NotImplementedError()

    def clear_transport(self):
        raise NotImplementedError()

    def on_close(self, reason, description):
        raise NotImplementedError()

    def setup_send_callback(self):
        raise NotImplementedError()

    def send(self, data, callback=None):
        self.send_packet('message', data, callback)
        return self

    def send_packet(self, type, data, callback=None):
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
        self.transport.send(wbuf)

        self.emit('drain')
        self.engine.emit('drain', self)

    def get_available_upgrades(self):
        all_upgrades = self.engine.upgrades(self.transport.name)
        available_upgrades = []

        for upgrade in all_upgrades:
            if upgrade in self.engine.transports:
                available_upgrades.append(upgrade)

        return available_upgrades

    def close(self):
        raise NotImplementedError()
