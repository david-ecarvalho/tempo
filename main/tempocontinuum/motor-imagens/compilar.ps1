# Compila o motor do Gerador de imagens e grava o resultado em site/js/motor/.
# Precisa (uma vez):  rustup target add wasm32-unknown-unknown
#                     cargo install wasm-bindgen-cli --version 0.2.100 --locked
# Uso: powershell -ExecutionPolicy Bypass -File motor-imagens\compilar.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
cargo build --release --target wasm32-unknown-unknown
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
wasm-bindgen --target web --no-typescript --out-dir ..\site\js\motor target\wasm32-unknown-unknown\release\motor_imagens.wasm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Copy-Item fonte\OFL.txt ..\site\js\motor\Montserrat-OFL.txt -Force
Get-ChildItem ..\site\js\motor | Select-Object Name, Length
