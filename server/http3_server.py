"""Servidor HTTP/3 (QUIC sobre UDP) minimalista com aioquic.

Serve arquivos estáticos de server/www e imprime no log, por requisição,
o stream QUIC usado — evidencia a multiplexação numa única conexão UDP.
Uso: python server/http3_server.py [--port 4433]
"""
import argparse
import asyncio
import mimetypes
import time
from pathlib import Path

from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import H3Event, HeadersReceived
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import ProtocolNegotiated, QuicEvent

ROOT = Path(__file__).parent / "www"
CERTS = Path(__file__).parent / "certs"


class Http3Server(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._http = None

    def quic_event_received(self, event: QuicEvent) -> None:
        if isinstance(event, ProtocolNegotiated) and event.alpn_protocol in H3_ALPN:
            self._http = H3Connection(self._quic)
        if self._http is not None:
            for h3_event in self._http.handle_event(event):
                self.http_event_received(h3_event)

    def http_event_received(self, event: H3Event) -> None:
        if not isinstance(event, HeadersReceived):
            return
        h = {k.decode(): v.decode() for k, v in event.headers}
        method, path = h.get(":method", "GET"), h.get(":path", "/").split("?")[0]
        status, body, ctype = self.resolve(path)
        print(f"[{time.strftime('%H:%M:%S')}] stream={event.stream_id:<3} "
              f"{method} {path} -> {status} (h3, QUIC/UDP)", flush=True)
        self._http.send_headers(event.stream_id, [
            (b":status", str(status).encode()),
            (b"content-type", ctype.encode()),
            (b"content-length", str(len(body)).encode()),
            (b"server", b"aioquic-demo"),
            (b"alt-svc", b'h3=":4433"; ma=60'),
        ])
        if method != "HEAD":
            self._http.send_data(event.stream_id, body, end_stream=True)
        else:
            self._http.send_data(event.stream_id, b"", end_stream=True)
        self.transmit()

    @staticmethod
    def resolve(path: str):
        rel = "index.html" if path == "/" else path.lstrip("/")
        f = (ROOT / rel).resolve()
        if ROOT.resolve() in f.parents and f.is_file():
            return 200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        return 404, b"<h1>404 Not Found</h1>", "text/html"


async def main(host: str, port: int):
    cfg = QuicConfiguration(is_client=False, alpn_protocols=H3_ALPN)
    cfg.load_cert_chain(CERTS / "cert.pem", CERTS / "key.pem")
    await serve(host, port, configuration=cfg, create_protocol=Http3Server)
    print(f"HTTP/3 ouvindo em UDP {host}:{port}  (Ctrl+C para sair)", flush=True)
    await asyncio.Future()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=4433)
    a = ap.parse_args()
    try:
        asyncio.run(main(a.host, a.port))
    except KeyboardInterrupt:
        pass
