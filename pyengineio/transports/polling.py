from pyengineio.transports.base import Transport

import logging

log = logging.getLogger(__name__)


class Polling(Transport):
    name = 'polling'
    upgrades_to = ['websocket', 'flashsocket']

    def on_request(self, handle):
        method = handle.environ.get('REQUEST_METHOD')

        if method == 'GET':
            self.on_poll_request(handle)
        elif method == 'POST':
            self.on_data_request(handle)
        else:
            raise NotImplementedError()

    def on_poll_request(self, handle):
        if self.handle:
            log.debug('request overlap')
            raise NotImplementedError()

        log.debug('setting handle')

        self.handle = handle

        # TODO onClose, cleanup

        self.writable = True
        self.emit('drain')

        # if we're still writable but had a pending close, trigger an empty send
        if self.writable and self.should_close:
            log.debug('triggering empty send to append close packet')
            self.send([{'type': 'noop'}])

    def send(self, packets):
        if self.should_close:
            log.debug('appending close packet to payload')
            packets.append({'type': 'close'})

            self.should_close()
            self.should_close = None

        # TODO encodePayload, write
        raise NotImplementedError()

    def write(self, data):
        log.debug('writing "%s"', data)
        self.do_write(data)
        self.writable = False

    def do_write(self, data):
        raise NotImplementedError()
