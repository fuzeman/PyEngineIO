from pyengineio.transports.polling import Polling

import json
import logging
import re
import urlparse

log = logging.getLogger(__name__)

RE_DOUBLE_SLASHES = r"\\\\n"
RE_SLASHES = r"(?<!\\)\\n"


class JSONP_Polling(Polling):
    name = 'polling-jsonp'

    def __init__(self, request):
        super(JSONP_Polling, self).__init__(request)

        self.head = '___eio[' + re.sub(r'[^0-9]', '', request.query.get('j', '')) + ']('
        self.foot = ');'

    def on_data(self, data):
        qs = dict(urlparse.parse_qsl(data, keep_blank_values=True))
        data = qs.get('d')

        if not data:
            return

        # client will send already escaped newlines as \\\\n and newlines as \\n
        # \\n must be replaced with \n and \\\\n with \\n
        data = re.sub(RE_SLASHES, '\n', data)
        data = re.sub(RE_DOUBLE_SLASHES, '\\n', data)

        super(JSONP_Polling, self).on_data(data)

    def do_write(self, data):
        if self.poll_handle is None:
            return

        if 'socket' not in self.poll_handle.__dict__:
            return

        # we must output valid javascript, not valid json
        # see: http://timelessrepo.com/json-isnt-a-javascript-subset
        data = json.dumps(data).replace('\u2028', '\\u2028')\
                               .replace('\u2029', '\\u2029')

        # prepare response
        data = self.head + data + self.foot

        # explicit UTF-8 is required for pages not served under utf
        headers = {
            'Content-Type': 'text/javascript; charset=UTF-8',
            'Content-Length': len(data)
        }

        # prevent XSS warnings on IE
        # https://github.com/LearnBoost/socket.io/pull/1333
        ua = self.poll_handle.headers['user-agent']

        if ua and (';MSIE' in ua or 'Trident/' in ua):
            headers['X-XSS-Protection'] = '0'

        self.poll_handle.start_response('200 OK', headers.items())
        self.poll_handle.write(data)

    def headers(self, handle, headers):
        log.debug('headers')
