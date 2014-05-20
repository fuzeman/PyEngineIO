from pyemitter import Emitter
from threading import Timer
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

        self.check_interval_timer = None
        self.upgrade_timeout_timer = None
        self.ping_timeout_timer = None

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

            'pingInterval': self.engine.ping_interval,
            'pingTimeout': self.engine.ping_timeout
        }))

        self.emit('open')
        self.set_ping_timeout()

    def on_packet(self, packet):
        if self.ready_state != 'open':
            log.debug('packet received with closed socket')
            return

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

        raise NotImplementedError()

    def on_error(self, error):
        log.debug('transport error')
        self.on_close('transport error', error)

    def set_ping_timeout(self):
        if self.ping_timeout_timer:
            self.ping_timeout_timer.cancel()

        def on_ping_timeout():
            self.on_close('ping timeout')

        timeout = self.engine.ping_interval + self.engine.ping_timeout

        self.ping_timeout_timer = Timer(timeout / 1000, on_ping_timeout)
        self.ping_timeout_timer.start()

    def set_transport(self, transport):
        self.transport = transport

        transport.once('error', self.on_error)\
                 .once('close', self.on_close)\
                 .on('packet', self.on_packet)\
                 .on('drain', lambda: self.flush())

    def maybe_upgrade(self, transport):
        log.debug(
            'might upgrade socket transport from "%s" to "%s"',
            self.transport.name, transport.name
        )

        # TODO upgrade timeout

        @transport.on('packet')
        def on_packet(packet):
            p_type = packet.get('type')
            p_data = packet.get('data')

            if p_type == 'ping' and p_data == 'probe':
                transport.send([{'type': 'pong', 'data': 'probe'}])
                # TODO clearInterval(self.checkIntervalTimer);
                # TODO self.checkIntervalTimer = setInterval(check, 100);
            elif p_type == 'upgrade' and self.ready_state == 'open':
                log.debug('got upgrade packet - upgrading')
                self.upgraded = True

                self.clear_transport()

                self.set_transport(transport)
                self.emit('upgrade', transport)

                self.set_ping_timeout()
                self.flush()

                # TODO clearInterval(self.checkIntervalTimer);
                # TODO self.checkIntervalTimer = null;
                # TODO clearTimeout(self.upgradeTimeoutTimer);
                transport.off('packet', on_packet)
            else:
                transport.close()

    def clear_transport(self):
        # silence further transport errors and prevent uncaught exceptions
        self.transport.off('error')

        self.ping_timeout_timer.cancel()
        self.ping_timeout_timer = None

        # TODO clearTimeout(this.pingIntervalTimer); ?

    def on_close(self, reason, description=None):
        if self.ready_state == 'closed':
            return

        # TODO properly cleanup and close socket

    def setup_send_callback(self):
        raise NotImplementedError()

    def write(self, data, callback=None):
        self.send_packet('message', data, callback)
        return self

    def send_packet(self, type, data=None, callback=None):
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
