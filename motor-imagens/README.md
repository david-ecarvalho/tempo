# Motor do Gerador de imagens (Rust → WebAssembly)

Desenha as imagens do Gerador de imagens, que fica no editor (`site/admin/`, na matéria e em Ferramentas).
Roda no navegador: nenhuma foto, logo ou texto é enviado a outro lugar.

- **Entrada:** o formato (um item de `site/dados/layouts-imagens.json`) e o que a pessoa preencheu.
- **Saída:** os pixels da imagem pronta, mais um relatório (tamanho do título, avisos).
- **A interface** (campos, botões, prévia, download) continua em `site/admin/gerador.js`,
  que só chama o motor.

## Pastas
| Caminho | O que é |
|---|---|
| `src/lib.rs` | API usada pela página (`Motor`, `renderizar`, `definir_imagem`) e montagem da imagem |
| `src/texto.rs` | Fonte embutida, medição, quebra de linhas e ajuste do título à área |
| `src/desenho.rs` | Cores, camadas, gradientes, desfoque ("vidro") e imagens |
| `src/layout.rs` | Leitura do JSON dos formatos e dos dados |
| `fonte/` | Montserrat Medium (licença SIL OFL, em `fonte/OFL.txt`), embutida no `.wasm` |
| `tests/motor.rs` | Testes: monta todos os formatos e lê o QR code com um decodificador independente |

## Compilar
Precisa do Rust (rustup). Uma vez só:

```
rustup target add wasm32-unknown-unknown
cargo install wasm-bindgen-cli --version 0.2.100 --locked
```

Depois de mudar o código:

```
powershell -ExecutionPolicy Bypass -File motor-imagens\compilar.ps1   # Windows
sh motor-imagens/compilar.sh                                     # Linux/macOS
```

O resultado vai para `site/js/motor/` (`motor_imagens.js` e `motor_imagens_bg.wasm`). É essa pasta que
o editor usa; a pasta `motor-imagens/` não precisa ser publicada.

Testes (rodam no PC, sem navegador): `cargo test --release`, dentro de `motor-imagens/`.

## Observações
- Usa o SIMD do WebAssembly (`.cargo/config.toml`), presente em todos os navegadores atuais
  (Chrome/Edge 91+, Firefox 89+, Safari 16.4+).
- Mudar formatos, cores ou medidas não exige recompilar: basta editar `site/dados/layouts-imagens.json`.
- O `.wasm` tem cerca de 1,4 MB (uns 500 KB com a compressão do servidor). Boa parte é a fonte e as
  tabelas de Unicode do rustybuzz.
