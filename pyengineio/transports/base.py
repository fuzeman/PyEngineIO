from pyemitter import Emitter


class Transport(Emitter):
    name = None

    def __init__(self):
        self.ready_state = 'opening'
        self.should_close = None
        self.writable = False

        self.sid = None

        self.handle = None

    def on_request(self, handle):
        raise NotImplementedError()

    def on_poll_request(self, handle):
        raise NotImplementedError()

    def on_data_request(self, handle):
        raise NotImplementedError()

    def on_data(self, data):
        raise NotImplementedError()

    def send(self, packets):
        raise NotImplementedError()

    def write(self, data):
        raise NotImplementedError()

    def do_close(self, callback=None):
        raise NotImplementedError()
