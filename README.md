# Tempo Continuum

Site do Tempo Continuum: notícias, fichas de políticos, votações do e-Cidadania, streaming, dossiês, cursos e
ferramentas de tecnologia cívica. É um site estático, publicado no GitHub Pages.

## Pastas

| Pasta | O que é |
|---|---|
| [`site/`](site/) | O site (páginas, `js/`, `dados/`, `conteudo/`, imagens) e o editor local (`site/admin/`). Veja [site/README.md](site/README.md). |
| [`motor-imagens/`](motor-imagens/) | Código em Rust do motor do Gerador de imagens. Compilado, vai para `site/js/motor/`. Veja [motor-imagens/README.md](motor-imagens/README.md). |
| [`.github/workflows/`](.github/workflows/) | Publicação automática no GitHub Pages. |
| `LEIA-ME.md`, `tempocontinuum.code-workspace` | Guia e espaço de trabalho do VS Code. |

## Publicação no GitHub Pages

1. No GitHub: **Settings › Pages › Build and deployment › Source = "GitHub Actions"** (uma vez só).
2. Cada push no `main` que mude algo em `site/` roda [`publicar-site.yml`](.github/workflows/publicar-site.yml):
   ele executa `site/scripts/publicar.py`, que refaz os índices de `site/dados/` e monta `site/_site/` só com o
   que é público. O editor (`admin/`), os scripts e a documentação ficam de fora.
3. O endereço fica em `https://<usuário>.github.io/<repositório>/`. Todos os caminhos do site são relativos,
   então ele funciona nesse subcaminho sem ajustes.

O editor de matérias (`site/admin/`) **não funciona no GitHub Pages**, porque grava os arquivos pelo servidor
local (`site/scripts/servidor.py`). O conteúdo é escrito no computador e publicado com um push.

## Rodar no computador

```
python3 site/scripts/servidor.py
```

Site em http://localhost:8000/ e editor em http://localhost:8000/admin/.

Para ver exatamente o que vai para o GitHub Pages:

```
python3 site/scripts/publicar.py
python3 -m http.server 8000 --directory site/_site
```
