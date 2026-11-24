# Av4 – HTTP/3 (Grupo 3). Rode `make help` para a lista de alvos.
PY      := .venv/bin/python
HOST    := 127.0.0.1
PORT    := 4433
CERTDIR := server/certs
PCAP    := output/h3.pcap
BROWSER ?= $(firstword $(foreach b,google-chrome google-chrome-stable chromium chromium-browser,$(shell command -v $(b) 2>/dev/null)))
PATHS   := /style.css /app.js /img/tile1.svg /img/tile2.svg /nada

.PHONY: help setup cert server client capture chrome check ports clean

help:   ## lista os alvos
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-9s %s\n", $$1, $$2}'

setup: .venv/.ok cert   ## cria venv, instala aioquic e gera certificado

.venv/.ok: requirements.txt
	python3 -m venv .venv
	.venv/bin/pip install -q -r requirements.txt
	touch $@

cert: $(CERTDIR)/cert.pem   ## gera certificado autoassinado + hash SPKI (Chrome)

$(CERTDIR)/cert.pem:
	mkdir -p $(CERTDIR)
	openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes \
	  -keyout $(CERTDIR)/key.pem -out $@ -days 14 -subj "/CN=localhost" \
	  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
	openssl x509 -in $@ -pubkey -noout | openssl pkey -pubin -outform der \
	  | openssl dgst -sha256 -binary | base64 > $(CERTDIR)/spki.txt

server: setup   ## T1: sobe o servidor HTTP/3 em UDP 4433
	$(PY) server/http3_server.py --host $(HOST) --port $(PORT)

client: setup   ## T3: 6 requisições paralelas numa única conexão QUIC
	$(PY) server/http3_client.py https://$(HOST):$(PORT)/ $(PATHS)

capture:   ## T2: tcpdump em lo (UDP 4433) -> output/h3.pcap (sudo)
	mkdir -p $(dir $(PCAP))
	sudo tcpdump -i lo -n udp port $(PORT) -w $(PCAP)

chrome: cert   ## abre Chrome/Chromium forçando QUIC e aceitando o certificado
	@test -n "$(BROWSER)" || { echo "instale google-chrome ou chromium (ou: make chrome BROWSER=caminho)"; exit 1; }
	$(BROWSER) --user-data-dir=/tmp/h3chrome \
	  --origin-to-force-quic-on=$(HOST):$(PORT) \
	  --ignore-certificate-errors-spki-list="$$(cat $(CERTDIR)/spki.txt)" \
	  https://$(HOST):$(PORT)/

check:   ## confere pré-requisitos (curl h3, tcpdump, chrome, validade do cert)
	@curl -V | grep -q HTTP3 && echo "curl: HTTP3 ok" || echo "curl: SEM HTTP3 (use make client)"
	@command -v tcpdump >/dev/null && echo "tcpdump: ok" || echo "tcpdump: faltando"
	@test -n "$(BROWSER)" && echo "navegador chromium: $(BROWSER)" || echo "navegador chromium: faltando (so Firefox?)"
	@command -v wireshark >/dev/null || command -v tshark >/dev/null && echo "wireshark/tshark: ok" || echo "wireshark/tshark: faltando"
	@openssl x509 -in $(CERTDIR)/cert.pem -noout -enddate 2>/dev/null || echo "cert: rode make cert"

ports:   ## mostra que o servidor escuta em UDP (não TCP)
	ss -ulnp | grep $(PORT) || echo "nada em UDP $(PORT)"

clean:   ## apaga cert/chaves e o pcap (para regerar do zero)
	rm -f $(CERTDIR)/cert.pem $(CERTDIR)/key.pem $(CERTDIR)/spki.txt $(PCAP)
