from pyengineio.transports.polling import Polling


class XHR_Polling(Polling):
    name = 'polling-xhr'

    def do_write(self, data):
        raise NotImplementedError()
