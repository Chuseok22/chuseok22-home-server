import ssl

from requests.adapters import HTTPAdapter


class LegacySSLAdapter(HTTPAdapter):
    """세종대 서버의 구형 TLS 설정과 호환되는 어댑터.

    Python 3.12 기본 SECLEVEL=2가 portal/libseat.sejong.ac.kr의 cipher suite와
    충돌하여 SSLV3_ALERT_HANDSHAKE_FAILURE가 발생하므로 SECLEVEL=1로 낮춘다.
    """

    def init_poolmanager(self, *args, **kwargs) -> None:
        from urllib3.util.ssl_ import create_urllib3_context
        ctx = create_urllib3_context()
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        kwargs['ssl_context'] = ctx
        super().init_poolmanager(*args, **kwargs)
