from pyengineio.engine import EngineIO
from pyengineio.handler import EngineIO_Handler

from gevent.wsgi import WSGIServer


class EngineIO_Server(WSGIServer):
    def __init__(self, listener, application, options=None, *args, **kwargs):
        if not 'handler_class' in kwargs:
            kwargs['handler_class'] = EngineIO_Handler

        super(EngineIO_Server, self).__init__(
            listener, application,
            *args, **kwargs
        )

        self.engine = EngineIO(options)

    def handle(self, socket, address):
        handler = self.handler_class(self.engine, socket, address, self)
        handler.handle()
