from pyengineio.transports.polling import Polling


class XHR_Polling(Polling):
    name = 'polling-xhr'

    def do_write(self, data):
        self.poll_handle.start_response('200 OK', [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Length', len(data)),
            ('Connection', 'close')
        ])

        self.poll_handle.write(data)
