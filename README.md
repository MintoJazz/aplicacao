# Av4 – HTTP/3 (Grupo 3) · Redes de Computadores, IFRS

Servidor e cliente HTTP/3 (QUIC sobre UDP) em Python com [aioquic](https://github.com/aiortc/aioquic), mais a documentação da apresentação.

## Rodar

```bash
make setup     # venv + aioquic + certificado autoassinado
make server    # terminal 1: UDP 4433
make client    # terminal 3: 6 requisições em 1 conexão QUIC
make help      # todos os alvos (capture, chrome, check, ports, clean)
```

## Nota sobre o curl

O curl do sistema (8.18) **não** foi compilado com HTTP/3, então `curl --http3` não funciona aqui. Por isso há `server/http3_client.py`. `make check` mostra isso.
