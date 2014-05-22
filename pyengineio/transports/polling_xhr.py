from pyengineio.transports.polling import Polling


class XHR_Polling(Polling):
    name = 'polling-xhr'

    def do_write(self, data):
        content_type = 'application/octet-stream'

        if not self.supports_binary:
            content_type = 'text/plain; charset=UTF-8'

        self.poll_handle.start_response('200 OK', [
            ('Content-Type', content_type),
            ('Content-Length', len(data)),
            ('Connection', 'close')
        ])

        self.poll_handle.write(data)
