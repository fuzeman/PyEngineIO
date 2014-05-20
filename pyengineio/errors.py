class Errors(object):
    UNKNOWN_TRANSPORT = 0
    UNKNOWN_SID = 1

    BAD_HANDSHAKE_METHOD = 2
    BAD_REQUEST = 3

    MESSAGES = {
        UNKNOWN_TRANSPORT: 'Transport unknown',
        UNKNOWN_SID: 'Session ID unknown',
        BAD_HANDSHAKE_METHOD: 'Bad handshake method',
        BAD_REQUEST: 'Bad request'
    }
