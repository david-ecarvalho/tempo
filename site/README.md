# Tempo Continuum

Site do Tempo Continuum: notícias, perfis de políticos, casos, streaming (documentários e vídeos do YouTube), dossiês, cursos com biblioteca e ferramentas de tecnologia cívica.

O site roda localmente para edição (veja "Rodar no computador") e é publicado como site estático (veja "Publicar o site"). O endereço antigo no GitHub Pages era https://tempocontinuum.github.io/tempocontinuum/.

## Como lançar matérias

Com o servidor local rodando (`python scripts/servidor.py`), abra http://localhost:8000/admin/ em qualquer navegador deste computador. O editor é próprio do site. Na lateral ficam as coleções (Matérias, Dossiês, Meta-dossiês, Publicações, Políticos, Casos, Vídeos, Curtos e Votações), com a contagem de cada uma; ao escolher uma, os itens aparecem em cartões, com a foto ou a capa, uma busca e o botão **+ Novo**. Clicar num cartão abre o formulário de edição (o botão **←** volta para os cartões). O editor sugere as tags e subtags que já existem, reduz as fotos ao enviar e mostra a prévia do texto enquanto você escreve. Cada matéria é gravada como um arquivo Markdown em `conteudo/noticias/`, e o servidor atualiza o índice sozinho. Não há etapa de revisão: salvou, aparece no site.

O botão **Arquivo Markdown** mostra e permite editar o arquivo inteiro, como ele fica gravado.

## Onde fica cada coisa

- `*.html` e `js/runtime.js`: as páginas do site.
- `conteudo/noticias/*.md`: uma matéria por arquivo Markdown. O cabeçalho entre linhas `---` guarda título, data, tags, foto etc.; o texto vem embaixo. A página `materia.html?id=<arquivo>` mostra a matéria.
- `conteudo/politicos/*.md`: uma ficha por arquivo Markdown. O cabeçalho guarda os dados, selos e eleições; o texto tem uma seção `## ` para Resumo, Trajetória, Atuação, Posições declaradas, Controvérsias e processos e Fontes. A página `ficha.html?id=<arquivo>` monta a ficha.
- `js/markdown.js`: lê e grava esses arquivos (usado pelas páginas e pelo editor). O formato completo está descrito no começo dele.
- `dados/noticias.json`, `dados/politicos.json` e `dados/votacoes.json`: índices gerados por `scripts/gerar-indice.py`. A Home e a página Notícias leem o primeiro; a página Políticos, o segundo; a página Votações, o terceiro (que já traz a descrição de cada votação).
- `conteudo/votacoes/*.md`: uma votação do e-Cidadania por arquivo. O cabeçalho guarda os dados da consulta, o placar e a `recomendacao` (`sim` ou `nao`); o texto é a nossa descrição.
- `scripts/ecidadania.py`: lê uma consulta pública do e-Cidadania (o editor usa pelo servidor local).
- `conteudo/videos/*.md`: um vídeo do YouTube por arquivo (só cabeçalho: `titulo`, `criador`, `link`, `capa`, `data`). Indexado em `dados/videos.json`, que a parte "Vídeos do YouTube" de `streaming.html` lê.
- `conteudo/curtos/*.md`: um vídeo curto por arquivo (cabeçalho com `titulo`, `link`, `plataforma`, `criador`, `data`, `capa` e `tags`; o texto, opcional, é a descrição). Indexado em `dados/curtos.json`, que `curtos.html` (Recursos › Repositório de Vídeos Curtos) lê.
- `imagens/materias/`, `imagens/politicos/` `imagens/videos/` e `imagens/curtos/`: fotos e capas enviadas pelo editor.
- `admin/`: o editor de matérias e fichas (`index.html`, `editor.js`, `editor.css`). Ele grava pelos endereços `/api/...` do servidor local, que só aceitam pedidos do próprio computador.
- `gerador-de-imagens.html` e `js/gerador-imagens.js`: o Gerador de imagens (Ferramentas). Monta a imagem num canvas no navegador de quem usa; nada é enviado ao site. Os formatos e as áreas de cada um ficam em `dados/layouts-imagens.json`. O desenho é feito por um motor em Rust compilado para WebAssembly (`js/motor/`; o código-fonte fica fora do site, em `../motor-imagens/`).
- `js/tags.js`: tags com subtag ("violência/contra indígenas"), usadas por Home, Notícias, Matéria e Casos.
- `scripts/servidor.py`: servidor local que refaz os índices sozinho.
- `scripts/publicar.py`: monta a versão publicável do site em `_site/` (veja "Publicar o site").
- `../.github/workflows/publicar-site.yml` (na raiz do repositório): publicação no GitHub Pages, usando `scripts/publicar.py`.

## Como lançar ou editar fichas de políticos

No editor, abra **Políticos** e crie uma ficha nova ou edite uma existente. Como as matérias, a ficha é gravada direto em `conteudo/politicos/`. Toda informação precisa estar nas fontes da ficha. O link "Ver histórico de edições" de cada ficha mostra todas as mudanças feitas nela.

## Como lançar votações do e-Cidadania

No editor, abra **Votações** e clique em **+ Nova votação**. Cole o link da consulta pública no e-Cidadania (por exemplo `https://www12.senado.leg.br/ecidadania/visualizacaomateria?id=173618`) ou só o número dela e clique em **Trazer do e-Cidadania**: o editor traz a sigla, a autoria, a ementa e o placar (o servidor lê a página do Senado, por isso precisa de internet). Depois escreva um título em linguagem simples, escolha a recomendação (**Vote SIM** ou **Vote NÃO**) e escreva a descrição em Markdown. Cada votação é gravada em `conteudo/votacoes/` e aparece em `votacoes.html` (link em Ferramentas), com o botão para votar no e-Cidadania.

O placar não se atualiza sozinho: abra a votação, clique em **Atualizar dados e votos** e salve. Para testar a leitura de uma consulta no terminal: `python scripts/ecidadania.py 173618`.

## Contatos de parlamentares

A página `contatos.html` (link em Recursos) mostra e-mail, telefone, gabinete, página oficial e redes sociais dos deputados federais, senadores e deputados estaduais e distritais em exercício, com busca e filtros por casa (Câmara, Senado, Assembleias), estado e partido. Quem usa pode copiar os e-mails da lista filtrada ou baixar uma planilha CSV.

A aba **Mapa por estado** tem um mapa do Brasil clicável (também funciona pelo teclado: Tab até o estado e Enter) e mostra, de um estado só, os senadores, os deputados federais e os deputados estaduais (ou distritais), separados por casa. Dá para passar de um estado ao outro pelas setas da página, pela faixa de siglas ou pelas setas ← → do teclado; o endereço `contatos.html#estado=SP` abre direto num estado. O desenho do mapa fica em `dados/mapa-ufs.json`, gerado por `scripts/gerar-mapa.py` a partir da malha oficial de estados do IBGE (só precisa rodar de novo para mudar o desenho).

Os dados ficam em `dados/parlamentares.json`. De onde vêm:

- **Câmara e Senado:** APIs oficiais de dados abertos (`scripts/parlamentares.py`).
- **Assembleias e CLDF:** não há base nacional, então `scripts/estaduais.py` lê o que cada casa publica. SP, MG e RS têm dados estruturados; AC, AL, PB, PI, RR e TO usam o SAPL (sistema do Interlegis, com API); as outras são lidas da página de cada deputado no site oficial. O que se repete em quase todos os perfis de um estado (telefone geral, ouvidoria, redes da própria Assembleia) é descartado.

Para atualizar (depois de eleições, trocas de partido ou suplentes que assumem), rode com internet:

```
python scripts/parlamentares.py
```

Leva uns 8 minutos. Com `--estaduais`, atualiza só as Assembleias. Se o site de uma Assembleia estiver fora do ar, os dados anteriores dela são mantidos e a página avisa. Para testar um estado sem gravar nada: `python scripts/estaduais.py RJ`.

Limites conhecidos: Goiás ainda não entrou (o site da Alego não respondeu às coletas); MT não publica e-mail nem telefone dos gabinetes; MS e TO não informam partido; o cadastro de AL lista mais parlamentares ativos do que cadeiras. Sites de Assembleia mudam de layout sem aviso: se um estado vier com contagem estranha, o script avisa (`<- esperado ~N`) e o coletor dele precisa de ajuste.

O script só guarda dados de contato do mandato, nada de CPF ou outros dados pessoais.

## Como adicionar vídeos do YouTube

No editor, abra **Vídeos** e clique em **+ Novo vídeo**. Cole o link do vídeo, escreva o nome do vídeo e o nome do criador, e escolha a capa: **Enviar imagem** (ou arraste uma) ou **Usar a miniatura do YouTube**. Ao salvar, o vídeo aparece em Streaming › Vídeos do YouTube (`streaming.html#youtube`); clicar no cartão abre o vídeo no YouTube, numa aba nova. A antiga página `documentarios.html` agora só redireciona para `streaming.html`.

## Meta-dossiês

Um meta-dossiê junta vários dossiês que já existem num documento só, para ler um tema de ponta a ponta. No editor, abra **Meta-dossiês**, clique em **+ Novo meta-dossiê**, escreva o título e escolha os dossiês em **Dossiês reunidos** (as setas mudam a ordem). Cada dossiê vira uma parte, com página de abertura (título, subtítulo e apresentação dele) e os seus capítulos, numerados do primeiro ao último. O texto continua sendo editado em cada dossiê: o meta-dossiê sempre mostra a versão salva de cada um.

O arquivo fica em `conteudo/metadossies/<id>.md` (o cabeçalho é o do dossiê, mais a lista `dossies`; o texto é a apresentação) e aparece em `dossie.html?meta=<id>` e na parte "Meta-dossiês" da página Dossiês. O botão **Gerar PDF** grava `arquivos/metadossies/<id>.pdf`. O PDF fica desatualizado quando o meta-dossiê ou qualquer dossiê reunido muda; aí é só gerar de novo.

## Casos acompanhados

No editor, abra **Casos** e clique em **+ Novo caso**. Preencha o título, a situação (Em andamento, Em julgamento ou Encerrado), a data de abertura, a última atualização e a última etapa, o resumo, os envolvidos (um por linha), os documentos (título e link de cada um) e as tags. Cada caso é gravado em `conteudo/casos/<id>.md` e indexado em `dados/casos.json`. Ele tem a sua página, `caso.html?id=<id>`, com a situação, a última etapa, o resumo, os envolvidos (com link para a ficha da Wiki quando o nome antes da vírgula for o de uma ficha), os documentos, as matérias sobre o caso e o dossiê de que faz parte. A lista de casos fica na Wiki (`politicos.html#casos`), com filtro por situação, tags e busca. Os endereços antigos (`casos.html` e `dossies.html#caso-<id>`) redirecionam.

As ligações entre matérias, dossiês, meta-dossiês e casos são feitas por tag, como a de uma matéria com a ficha de um político: um item com o título de outro entre as tags fica ligado a ele, e as duas páginas mostram uma à outra (quadros para casos, dossiês e meta-dossiês; a lista "Matérias relacionadas" para matérias). Dossiê e meta-dossiê também ficam ligados quando o dossiê está na lista do meta-dossiê. As regras ficam em `js/ligacoes.js`.

No editor, a seção **Ligações** (no fim do formulário de matérias, dossiês, meta-dossiês e casos) mostra tudo o que está ligado ao item, nos dois sentidos, com os botões **Abrir** e **Desligar**. Para ligar, escolha o tipo e o item e clique em **+ Ligar**: a tag com o título do outro item entra neste item (salve para valer no site). De um dossiê, ligar a um meta-dossiê põe o dossiê na lista do meta-dossiê; de um meta-dossiê, ligar a um dossiê o acrescenta em "Dossiês reunidos". Desligar uma ligação feita pelo outro item tira a tag dele e o salva na hora. Se o título de um item mudar, as tags que apontam para ele precisam ser refeitas.

## Dossiês impressos

A página Publicações tem a parte **Dossiês impressos** (`publicacoes.html#dossies-impressos`), com todos os dossiês e meta-dossiês na versão para imprimir. Quando o PDF foi gerado pelo editor e está em dia, o botão é **Baixar PDF**; senão, **Imprimir / salvar PDF** abre a versão impressa com a janela de impressão do navegador ("Salvar como PDF").

O PDF é gerado com o Edge, o Chrome, o Chromium ou o Brave do computador. Se o navegador estiver em outro lugar, informe o caminho na variável `TC_NAVEGADOR` antes de iniciar o servidor.

## Repositório de Vídeos Curtos

A página `curtos.html` (cartão em Recursos) reúne vídeos curtos de qualquer plataforma: YouTube (Shorts), TikTok, Instagram (Reels), Kwai, X, Facebook, Threads, Bluesky ou outra. Quem visita filtra por plataforma, por uma ou mais tags (com subtags, como nas notícias) e por palavra; o botão "Assistir" abre o vídeo na plataforma de origem, numa aba nova.

Para adicionar: no editor, abra **Curtos** e clique em **+ Novo vídeo curto**. Cole o link (a plataforma é reconhecida sozinha, mas dá para trocar), escreva o título e, se quiser, o criador e uma descrição curta, e coloque de 1 a 8 tags. O editor sugere as tags que já existem nos vídeos curtos. A capa é opcional: para YouTube há o botão **Usar a miniatura do YouTube**; nas outras plataformas, envie um print. Sem capa, o cartão mostra o nome da plataforma numa cor própria. O endereço `curtos.html#<id>` leva direto ao vídeo.

## Rodar no computador

```
python scripts/servidor.py
```

Depois abra http://localhost:8000 (site) e http://localhost:8000/admin/ (editor). Com `--rede`, outros aparelhos do mesmo Wi-Fi também abrem o site.

## Publicar o site

```
python scripts/publicar.py
```

Monta em `_site/` a versão para a internet: refaz os índices de `dados/` e copia só o que o público usa (páginas, `js/`, `dados/`, `conteudo/`, `imagens/`, `logos/`, `arquivos/`). Fica de fora o editor (`admin/`), que só funciona com o servidor local: no site publicado não há como editar nada, e o conteúdo continua sendo lançado pelo editor local e publicado de novo. Todos os dossiês são publicados, inclusive os que ainda estão com o texto-modelo do editor.

`_site/` é um site estático comum (não está no Git) e pode ir para qualquer hospedagem:

- **GitHub Pages:** com Settings › Pages › Source = "GitHub Actions", cada push no `main` que mexa em `site/` roda `.github/workflows/publicar-site.yml` (na raiz do repositório), que usa este mesmo script.
- **Netlify ou Cloudflare Pages:** comando de build `python3 scripts/publicar.py`, pasta de publicação `_site`. Ou arraste a pasta `_site/` no painel.
- **Servidor próprio:** copie o conteúdo de `_site/` para a pasta pública do servidor.

Para conferir antes de enviar: `python -m http.server 8000 --directory _site` e abra http://localhost:8000.

Os PDFs dos dossiês (`arquivos/dossies/`) só são gerados pelo editor local; se o PDF de um dossiê não existir, o botão "Baixar PDF" abre a impressão do navegador.
