# Tempo Continuum: espaço de trabalho local

## Abrir
1. Descompacte esta pasta (por exemplo em `Documentos\tempocontinuum`).
2. No VS Code: **Arquivo › Abrir Espaço de Trabalho a partir do Arquivo…** e escolha `tempocontinuum.code-workspace`.
3. Se o VS Code perguntar se confia nos autores da pasta, responda que sim (as tarefas abaixo só funcionam assim).

Precisa ter instalados: **Git para Windows** e **Python 3** (marque "Add python.exe to PATH" na instalação).

## O que tem aqui
| Pasta | O que é | Git |
|---|---|---|
| `site/` | O site, igual ao `main` do GitHub no commit `d06274c` | Já ligado a `github.com/tempocontinuum/tempocontinuum` |
| `motor-imagens/` | Código em Rust do motor do Gerador de imagens; compilado, vai para `site/js/motor/` (veja o README dela) | Ainda sem repositório |

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
- **Motor de imagens: compilar**: rode depois de mudar o código em `motor-imagens/`
- **Motor de imagens: testar**
- **Site: buscar ramos do GitHub**: use quando o acesso ao GitHub voltar

## Sobre os outros ramos
Quando esta cópia foi feita, o GitHub estava recusando o acesso ("conta suspensa"), então só o `main` está aqui,
com os últimos commits. Quando o acesso voltar, a tarefa "Site: buscar ramos do GitHub" baixa o histórico completo
e todos os ramos (como `remover-ficticio-subtags`, do PR #12). Para juntar um ramo ao seu `main` local:

```
git merge origin/remover-ficticio-subtags
```

Antes do primeiro commit seu, configure seu nome no git:
```
git config --global user.name "Seu Nome"
git config --global user.email "seu@email"
```
