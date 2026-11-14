# Tempo Continuum: espaço de trabalho local

## Abrir
1. Clone o repositório (ou descompacte esta pasta, por exemplo em `Documentos\tempocontinuum`).
2. No VS Code: **Arquivo › Abrir Espaço de Trabalho a partir do Arquivo…** e escolha `tempocontinuum.code-workspace`.
3. Se o VS Code perguntar se confia nos autores da pasta, responda que sim (as tarefas abaixo só funcionam assim).

Precisa ter instalados: **Git para Windows** e **Python 3** (marque "Add python.exe to PATH" na instalação).

## O que tem aqui
| Pasta | O que é | Git |
|---|---|---|
| `site/` | O site (páginas, conteúdo e o editor local em `site/admin/`) | Neste repositório |
| `motor-imagens/` | Código em Rust do motor do Gerador de imagens; compilado, vai para `site/js/motor/` (veja o README dela) | Neste repositório |
| `.github/workflows/` | Publicação automática no GitHub Pages a cada push no `main` (veja o `README.md`) | Neste repositório |

O histórico aparece na aba **Controle do Código-Fonte** (Ctrl+Shift+G).

## Rodar o site neste computador
Na pasta `site`, rode (ou use a tarefa "Site: abrir no navegador"):

```
python scripts/servidor.py
```

- **Site:** http://localhost:8000/
- **Editor de matérias e fichas:** http://localhost:8000/admin/, em qualquer navegador deste computador. É um
  editor próprio: grava cada matéria e cada ficha como um arquivo Markdown (`.md`) em `site/conteudo/`, sem GitHub
  nem login. Não há etapa de revisão: salvou, está no site local.
- **Dossiês:** na aba "Dossiês" do editor, cada linha `## Título` do texto abre um capítulo. O botão **Gerar PDF**
  salva e cria `site/arquivos/dossies/<id>.pdf` (com capa, sumário e um capítulo por página) usando o Edge deste
  computador, sem abrir janela. A página `dossie.html?id=…` mostra o dossiê e o botão "Baixar PDF"; se o PDF não
  existir ou estiver desatualizado, o botão abre a impressão do navegador ("Salvar como PDF").
- **Índices automáticos:** quando uma matéria ou ficha é criada, alterada ou apagada (pelo editor ou à mão em
  `conteudo/`), o servidor refaz `dados/noticias.json` e `dados/politicos.json` na próxima vez que uma página pedir.
- **Outros aparelhos (celular, outro PC no mesmo Wi-Fi):** `python scripts/servidor.py --rede` mostra o endereço
  a abrir. O Windows pode pedir para liberar o Python no firewall. O editor só funciona no próprio computador.
- Tudo funciona sem internet, menos a fonte Montserrat, que vem do Google Fonts: sem conexão, as páginas usam Arial.

## Tarefas prontas
**Terminal › Executar Tarefa…**
- **Site: abrir no navegador (servidor local)**: site em http://localhost:8000 e editor em /admin/
- **Site: servidor local acessível na rede**: para abrir no celular ou em outro PC
- **Motor de imagens: compilar**: rode depois de mudar o código em `motor-imagens/` (no Linux: `sh motor-imagens/compilar.sh`)
- **Motor de imagens: testar**

## Publicar
Faça commit e push no `main`. O GitHub Actions monta o site com `site/scripts/publicar.py` e publica no GitHub
Pages (é preciso escolher, uma vez, **Settings › Pages › Source = "GitHub Actions"**). O editor `admin/` não vai
para o site publicado.

## Histórico antigo
O histórico completo do site e os ramos antigos (como `remover-ficticio-subtags`, do PR #12) estão em
`github.com/tempocontinuum/tempocontinuum`. Na época desta cópia, o GitHub recusava o acesso a essa conta
("conta suspensa").

Antes do primeiro commit seu, configure seu nome no git:
```
git config --global user.name "Seu Nome"
git config --global user.email "seu@email"
```
