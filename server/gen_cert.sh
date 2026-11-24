#!/usr/bin/env bash
# Gera certificado autoassinado para localhost (QUIC exige TLS 1.3)
set -e
cd "$(dirname "$0")"
mkdir -p certs
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes \
  -keyout certs/key.pem -out certs/cert.pem -days 14 \
  -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
# SPKI hash (para --ignore-certificate-errors-spki-list do Chrome)
openssl x509 -in certs/cert.pem -pubkey -noout | openssl pkey -pubin -outform der \
  | openssl dgst -sha256 -binary | base64 | tee certs/spki.txt
