"""Cliente HTTP/3 mínimo: busca várias URLs em paralelo numa ÚNICA conexão QUIC.
Uso: python server/http3_client.py https://localhost:4433/ /style.css /app.js
"""
import asyncio
import sys
from urllib.parse import urlparse

from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import DataReceived, HeadersReceived
from aioquic.quic.configuration import QuicConfiguration


class Client(QuicConnectionProtocol):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.http = H3Connection(self._quic)
        self.waiters, self.resp = {}, {}

    def quic_event_received(self, event):
        for e in self.http.handle_event(event):
            if isinstance(e, HeadersReceived):
                self.resp[e.stream_id]["headers"] = dict(e.headers)
            elif isinstance(e, DataReceived):
                self.resp[e.stream_id]["size"] += len(e.data)
                if e.stream_ended:
                    self.waiters[e.stream_id].set_result(None)

    async def get(self, authority, path):
        sid = self._quic.get_next_available_stream_id()
        self.resp[sid] = {"size": 0, "path": path}
        self.waiters[sid] = asyncio.get_event_loop().create_future()
        self.http.send_headers(sid, [(b":method", b"GET"), (b":scheme", b"https"),
                                     (b":authority", authority.encode()), (b":path", path.encode())])
        self.http.send_data(sid, b"", end_stream=True)
        self.transmit()
        await self.waiters[sid]
        return sid


async def main(url, extra):
    u = urlparse(url)
    cfg = QuicConfiguration(is_client=True, alpn_protocols=H3_ALPN, verify_mode=0)  # cert autoassinado
    async with connect(u.hostname, u.port or 443, configuration=cfg, create_protocol=Client) as c:
        print(f"ALPN negociado: {c._quic.tls.alpn_negotiated}  (h3 = HTTP/3 sobre QUIC/UDP)")
        paths = [u.path or "/"] + extra
        sids = await asyncio.gather(*(c.get(f"{u.hostname}:{u.port}", p) for p in paths))
        for sid in sids:
            r = c.resp[sid]
            print(f"stream {sid:<3} {r['path']:<14} status={r['headers'][b':status'].decode()} bytes={r['size']}")
        print(f"{len(sids)} requisições em 1 conexão QUIC, streams independentes")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2:]))
