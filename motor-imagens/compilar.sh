#!/usr/bin/env sh
# Compila o motor do Gerador de imagens e grava o resultado em site/js/motor/ (equivalente a compilar.ps1).
# Precisa (uma vez):  rustup target add wasm32-unknown-unknown
#                     cargo install wasm-bindgen-cli --version 0.2.100 --locked
# Uso: sh motor-imagens/compilar.sh
set -e
cd "$(dirname "$0")"
cargo build --release --target wasm32-unknown-unknown
wasm-bindgen --target web --no-typescript --out-dir ../site/js/motor target/wasm32-unknown-unknown/release/motor_imagens.wasm
cp fonte/OFL.txt ../site/js/motor/Montserrat-OFL.txt
ls -l ../site/js/motor
