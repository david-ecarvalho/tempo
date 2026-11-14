---
titulo: "Jellyfin: canal Tecnologia e Classe ensina a montar um “Netflix” privado em casa"
linha: "Em tutorial, o TeClas mostra como instalar um servidor de mídia livre e gratuito para organizar músicas, filmes e séries sem assinatura, sem propaganda e sem entregar dados a empresas"
data: "2026-11-12T23:47:00"
editoria: "Formação"
tags: ["tecnologia", "software livre", "privacidade", "Jellyfin"]
autor: "Redação"
foto: "https://i.ytimg.com/vi/vWUWZpDP63E/maxresdefault.jpg"
legenda: "Miniatura do vídeo “Jellyfin: crie seu próprio servidor de mídia”, do canal Tecnologia e Classe"
credito: "Reprodução / YouTube, Tecnologia e Classe (TeClas)"
destaque: false
---

O canal **Tecnologia e Classe (TeClas)** publicou nesta quinta-feira (12) um tutorial de cerca de 29 minutos sobre o **Jellyfin**, um programa livre e gratuito que transforma um computador comum num servidor de mídia. A ideia é ter um “Netflix” e um “Spotify” próprios: os filmes, séries e músicas ficam guardados em casa e podem ser vistos no navegador, no celular, no tablet ou na smart TV, sem assinatura e sem propaganda.

O vídeo faz parte de uma série do canal sobre como hospedar, na própria infraestrutura, alternativas a serviços famosos, a prática conhecida como *homelab*. Esta matéria resume o conteúdo; o tutorial completo, com os comandos, está [no canal do TeClas](https://www.youtube.com/watch?v=vWUWZpDP63E).

## Por que o Jellyfin

O apresentador explica que existem programas parecidos, como Plex e Emby, mas que eles têm modelos de negócio baseados em assinatura, componentes fechados e algum compartilhamento de dados. Para ele, esse modelo pode comprometer a privacidade de quem usa.

O Jellyfin, ao contrário, é um projeto de código aberto, mantido pela comunidade, e funciona inteiro dentro da rede de casa. “Se tu desligar o cabo do teu roteador pra rua, tu ainda tem toda a tua coleção rodando”, resume. O projeto também tem uma comunidade ativa, com muitos tutoriais e complementos (*plugins*).

O uso que ele mesmo faz é um bom exemplo: uma coleção de músicas reunida ao longo de mais de 20 anos, espalhada por HDs e computadores antigos, que o Jellyfin juntou numa só biblioteca, com capas, organização e uma interface parecida com a dos serviços comerciais.

## O que é preciso

Não é necessário um computador potente. Um notebook antigo, um minicomputador ou um Raspberry Pi mais recente dão conta. O notebook tem a vantagem de gastar menos energia e fazer menos barulho que um computador de mesa. O vídeo lista os pontos de atenção:

- **Espaço em disco** para os arquivos de mídia e para os arquivos temporários que o programa gera;
- **Processamento** para a *transcodificação*, que converte um vídeo ou uma música para o formato que cada aparelho consegue tocar. Uma placa de vídeo, mesmo a integrada do notebook, deixa isso mais rápido;
- Um sistema **Linux, Windows ou macOS**. No Windows, há um instalador de um clique. No Linux, o site oficial oferece um script de instalação, e o tutorial mostra como conferir se o arquivo baixado não foi alterado antes de rodá-lo.

## Instalação e primeiros passos

Depois de instalado, o Jellyfin abre no navegador, no endereço do computador, na porta 8096. Nessa primeira tela, a pessoa escolhe o idioma (há português do Brasil), cria a conta de administrador e indica as pastas de músicas e de filmes. O programa busca sozinho capas, descrições e informações de cada álbum e filme.

O tutorial antecipa um problema comum no Linux: o Jellyfin pode não ter permissão para ler as pastas da pessoa. O comando que resolve isso, tirado da documentação oficial, está no roteiro do vídeo.

O apresentador também recomenda uma **senha forte** para a conta de administrador, principalmente se o servidor for acessado de fora de casa.

## Contas, plugins e aplicativos

No painel de administração dá para criar contas para outras pessoas e escolher o que cada uma vê. Uma família pode, por exemplo, deixar só os desenhos animados disponíveis na conta das crianças. Também é possível mudar o visual do servidor e instalar plugins que acrescentam funções.

Para ouvir música, o vídeo indica os aplicativos **Feishin** (computador e navegador), **Supersonic** (computador, mais leve) e **Finamp** (celular, também disponível na loja F-Droid). Para filmes e séries, o navegador do celular já funciona bem, e muitas smart TVs têm o aplicativo oficial do Jellyfin na loja.

## Dicas para ir além

Na parte final, o TeClas reúne dicas práticas:

- **Ouvir fora de casa:** em vez de abrir o servidor para toda a internet, o canal recomenda uma VPN como **Netbird** ou **Tailscale**, que só dá acesso aos aparelhos da própria pessoa. O canal tem um tutorial separado sobre isso;
- **Quick Connect:** um código para entrar sem digitar usuário e senha, útil na TV e no tablet;
- **Letras de músicas** sincronizadas, com o plugin LrcLib, que funcionou até com bandas independentes brasileiras;
- **MusicBrainz**, para corrigir álbuns identificados errado, além de capas e fotos de artistas que podem ser colocadas à mão nas pastas;
- Plugins da comunidade indicados por **Iago**, um dos editores do canal, que montou o próprio servidor personalizado: pular a abertura das séries (Intro Skipper), baixar legendas automaticamente (Open Subtitles) e tocar em aparelhos como o PlayStation 4 por DLNA.

Em todo o vídeo, o apresentador reforça que o tutorial é um ponto de partida: “usem o que vocês acharem melhor”.

## Créditos

Esta matéria é um resumo do vídeo [“JELLYFIN: CRIE SEU PRÓPRIO SERVIDOR DE MÍDIA [Tutorial]”](https://www.youtube.com/watch?v=vWUWZpDP63E), publicado em 12 de novembro de 2026 pelo canal [Tecnologia e Classe (TeClas)](https://www.youtube.com/@TecnologiaeClasse). Todo o conteúdo técnico, as explicações e as recomendações são do canal. Segundo a descrição do vídeo, a miniatura é de Pedro Luiz e a introdução, de Bryan Oliver. O vídeo foi patrocinado pela loja Insider.

Para apoiar o trabalho do canal: [apoia.se/tecnologiaeclasse](https://apoia.se/tecnologiaeclasse). Mais informações sobre o programa no site oficial, [jellyfin.org](https://jellyfin.org).
