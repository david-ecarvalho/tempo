"""Gera os índices do site a partir dos arquivos gravados pelo editor.

Matérias e fichas são arquivos Markdown (.md) com um cabeçalho de dados entre linhas "---"
(veja js/markdown.js). Arquivos .json antigos ainda são lidos, se não houver um .md de mesmo nome.

- dados/noticias.json, com as matérias de conteudo/noticias/. A Home e a página
  Notícias leem este índice; o texto completo de cada matéria é lido do arquivo
  dela, na página materia.html.
- dados/politicos.json, com as fichas de conteudo/politicos/. A página Políticos
  lê este índice; a ficha completa é lida do arquivo dela, na página ficha.html.
- dados/votacoes.json, com as consultas do e-Cidadania de conteudo/votacoes/, já com a
  descrição escrita por nós. A página votacoes.html lê só este índice.
- dados/videos.json, com os vídeos do YouTube de conteudo/videos/ (título, criador, capa e link).
- dados/publicacoes.json, com os livros e revistas de conteudo/publicacoes/ ({"livros": [...], "revistas": [...]}).
  A parte "Vídeos do YouTube" da página streaming.html lê este índice.
- dados/dossies.json, com os dossiês de conteudo/dossies/ (título, capa, número de capítulos e, se já foi
  gerado, o PDF em arquivos/dossies/<id>.pdf). A página dossies.html lê este índice; o texto é lido em dossie.html.
- dados/curtos.json, com os vídeos curtos de conteudo/curtos/ (título, link, plataforma, criador, data, capa,
  tags e descrição). A página curtos.html (Repositório de Vídeos Curtos, em Recursos) lê só este índice.
- dados/metadossies.json, com os meta-dossiês de conteudo/metadossies/: cada um junta vários dossiês, na ordem
  escolhida, num documento só (dossie.html?meta=<id>). Traz os dossiês que existem, o total de capítulos e, se
  estiver em dia, o PDF em arquivos/metadossies/<id>.pdf. As páginas dossies.html e publicacoes.html leem este índice.
- dados/casos.json, com os casos acompanhados de conteudo/casos/ (situação, datas, etapa, envolvidos, documentos,
  tags e resumo). A página de cada caso (caso.html?id=<id>) e a lista "Casos acompanhados" da Wiki
  (politicos.html#casos) leem este índice.

Uso: python3 scripts/gerar-indice.py
"""
import contextlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cabecalho  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "conteudo" / "noticias"
SAIDA = RAIZ / "dados" / "noticias.json"
PASTA_POLITICOS = RAIZ / "conteudo" / "politicos"
SAIDA_POLITICOS = RAIZ / "dados" / "politicos.json"
CAMPOS_POLITICOS = ("nome", "iniciais", "foto", "categoria", "cargo_curto", "partido", "uf", "chamada")
PASTA_VOTACOES = RAIZ / "conteudo" / "votacoes"
SAIDA_VOTACOES = RAIZ / "dados" / "votacoes.json"
CAMPOS_VOTACOES = ("titulo", "sigla", "identificacao", "autoria", "ementa", "recomendacao", "data", "apurado_em")
PASTA_VIDEOS = RAIZ / "conteudo" / "videos"
SAIDA_VIDEOS = RAIZ / "dados" / "videos.json"
CAMPOS_VIDEOS = ("titulo", "criador", "foto_criador", "capa", "link", "data")
PASTA_PUBLICACOES = RAIZ / "conteudo" / "publicacoes"
SAIDA_PUBLICACOES = RAIZ / "dados" / "publicacoes.json"
CAMPOS_PUBLICACOES = ("titulo", "autoria", "editora", "ano", "edicao", "data", "capa", "link", "rotulo_link")
PASTA_DOSSIES = RAIZ / "conteudo" / "dossies"
SAIDA_DOSSIES = RAIZ / "dados" / "dossies.json"
CAMPOS_DOSSIES = ("titulo", "linha", "data", "editado", "autor", "capa")
PASTA_PDF_DOSSIES = RAIZ / "arquivos" / "dossies"
PASTA_METADOSSIES = RAIZ / "conteudo" / "metadossies"
SAIDA_METADOSSIES = RAIZ / "dados" / "metadossies.json"
PASTA_PDF_METADOSSIES = RAIZ / "arquivos" / "metadossies"
PASTA_CASOS = RAIZ / "conteudo" / "casos"
SAIDA_CASOS = RAIZ / "dados" / "casos.json"
STATUS_CASO = ("Em andamento", "Em julgamento", "Encerrado")
PASTA_CURTOS = RAIZ / "conteudo" / "curtos"
SAIDA_CURTOS = RAIZ / "dados" / "curtos.json"
CAMPOS_CURTOS = ("titulo", "link", "plataforma", "criador", "data", "capa")
CAMPOS = ("titulo", "linha", "data", "editoria", "tags", "autor", "foto", "destaque")


def caminho_relativo(foto):
    """O editor grava fotos como /imagens/...; o site precisa de imagens/... ."""
    foto = (foto or "").strip()
    if foto.startswith("http://") or foto.startswith("https://"):
        return foto
    return foto.lstrip("/").removeprefix("tempocontinuum/")


def limpar_tag(tag):
    """Tag com subtag: "violência / contra indígenas" vira "violência/contra indígenas"."""
    return re.sub(r"\s*/\s*", "/", " ".join(str(tag).split()))


def arquivos(pasta):
    """Os .md da pasta, mais os .json antigos que não têm .md de mesmo nome."""
    md = sorted(pasta.glob("*.md"))
    nomes = {a.stem for a in md}
    return sorted(md + [a for a in pasta.glob("*.json") if a.stem not in nomes])


def ler(arquivo):
    texto = arquivo.read_text(encoding="utf-8")
    if arquivo.suffix == ".md":
        dados, _ = cabecalho.ler(texto)
        return dados
    dados = json.loads(texto)
    if not isinstance(dados, dict):
        raise ValueError("o arquivo não é um objeto")
    return dados


def main():
    materias, problemas = [], []
    for arquivo in arquivos(PASTA):
        try:
            dados = ler(arquivo)
        except (OSError, ValueError) as erro:
            problemas.append(f"{arquivo.name}: arquivo inválido ({erro})")
            continue
        if not dados.get("titulo") or not dados.get("data"):
            problemas.append(f"{arquivo.name}: sem título ou sem data, ficou de fora")
            continue
        item = {"id": arquivo.stem}
        for campo in CAMPOS:
            item[campo] = dados.get(campo)
        tags = item["tags"] if isinstance(item["tags"], list) else ([item["tags"]] if item["tags"] else [])
        item["tags"] = [limpar_tag(t) for t in tags if str(t).strip()]
        item["data"] = str(item["data"])
        item["foto"] = caminho_relativo(item["foto"])
        item["destaque"] = bool(item["destaque"])
        materias.append(item)

    materias.sort(key=lambda m: str(m["data"]), reverse=True)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(materias, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    print(f"{len(materias)} matérias em {SAIDA.relative_to(RAIZ)}")
    problemas += gerar_politicos()
    problemas += gerar_votacoes()
    problemas += gerar_videos()
    problemas += gerar_publicacoes()
    problemas += gerar_dossies()
    problemas += gerar_curtos()
    problemas += gerar_metadossies()
    problemas += gerar_casos()
    for problema in problemas:
        print(f"Aviso: {problema}", file=sys.stderr)


def gerar_politicos():
    """Grava dados/politicos.json e devolve a lista de avisos."""
    fichas, problemas = [], []
    for arquivo in arquivos(PASTA_POLITICOS):
        try:
            dados = ler(arquivo)
        except (OSError, ValueError) as erro:
            problemas.append(f"{arquivo.name}: arquivo inválido ({erro})")
            continue
        if not dados.get("nome"):
            problemas.append(f"{arquivo.name}: sem nome, ficou de fora")
            continue
        item = {"id": arquivo.stem}
        for campo in CAMPOS_POLITICOS:
            item[campo] = str(dados.get(campo) or "")
        item["foto"] = caminho_relativo(item["foto"])
        fichas.append(item)

    fichas.sort(key=lambda f: f["nome"].casefold())
    SAIDA_POLITICOS.write_text(json.dumps(fichas, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(fichas)} fichas em {SAIDA_POLITICOS.relative_to(RAIZ)}")
    return problemas


def gerar_votacoes():
    """Grava dados/votacoes.json (com a descrição de cada votação) e devolve a lista de avisos."""
    votacoes, problemas = [], []
    for arquivo in sorted(PASTA_VOTACOES.glob("*.md")):
        try:
            texto = arquivo.read_text(encoding="utf-8")
            dados, corpo = cabecalho.ler(texto)
        except (OSError, ValueError) as erro:
            problemas.append(f"{arquivo.name}: arquivo inválido ({erro})")
            continue
        try:
            numero = int(dados.get("ecidadania_id") or 0)
        except (TypeError, ValueError):
            numero = 0
        if not dados.get("titulo") or not numero:
            problemas.append(f"{arquivo.name}: sem título ou sem número da consulta, ficou de fora")
            continue
        item = {"id": arquivo.stem, "ecidadania_id": numero}
        for campo in CAMPOS_VOTACOES:
            item[campo] = str(dados.get(campo) or "")
        for campo in ("votos_sim", "votos_nao"):
            try:
                item[campo] = max(0, int(dados.get(campo) or 0))
            except (TypeError, ValueError):
                item[campo] = 0
        item["descricao"] = corpo
        votacoes.append(item)

    votacoes.sort(key=lambda v: v["data"], reverse=True)
    SAIDA_VOTACOES.write_text(json.dumps(votacoes, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(votacoes)} votações em {SAIDA_VOTACOES.relative_to(RAIZ)}")
    return problemas


def gerar_videos():
    """Grava dados/videos.json e devolve a lista de avisos."""
    videos, problemas = [], []
    for arquivo in sorted(PASTA_VIDEOS.glob("*.md")) if PASTA_VIDEOS.exists() else []:
        try:
            dados = ler(arquivo)
        except (OSError, ValueError) as erro:
            problemas.append(f"{arquivo.name}: arquivo inválido ({erro})")
            continue
        link = str(dados.get("link") or "").strip()
        if not dados.get("titulo") or not re.match(r"^https?://", link, re.I):
            problemas.append(f"{arquivo.name}: sem título ou sem link, ficou de fora")
            continue
        item = {"id": arquivo.stem}
        for campo in CAMPOS_VIDEOS:
            item[campo] = str(dados.get(campo) or "").strip()
        item["capa"] = caminho_relativo(item["capa"])
        item["foto_criador"] = caminho_relativo(item["foto_criador"])
        videos.append(item)

    videos.sort(key=lambda v: v["data"], reverse=True)
    SAIDA_VIDEOS.write_text(json.dumps(videos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(videos)} vídeos em {SAIDA_VIDEOS.relative_to(RAIZ)}")
    return problemas


def texto_simples(md):
    """Descrição para a página: o texto do arquivo sem as marcas de Markdown, parágrafos separados por linha em branco."""
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)                  # imagens
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)               # links: só o texto
    t = re.sub(r"(\*\*|__|\*|_)(.+?)\1", r"\2", t)               # negrito e itálico
    t = re.sub(r"^\s*(#{1,6}\s+|>\s?|[-*+]\s+|\d+[.)]\s+)", "", t, flags=re.M)
    return "\n\n".join(" ".join(p.split()) for p in re.split(r"\n\s*\n", t) if p.strip())


def gerar_publicacoes():
    """Grava dados/publicacoes.json ({"livros": [...], "revistas": [...]}) e devolve a lista de avisos."""
    grupos, problemas = {"livros": [], "revistas": []}, []
    for arquivo in sorted(PASTA_PUBLICACOES.glob("*.md")) if PASTA_PUBLICACOES.exists() else []:
        try:
            dados, corpo = cabecalho.ler(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            problemas.append(f"{arquivo.name}: arquivo inválido ({erro})")
            continue
        tipo = str(dados.get("tipo") or "")
        if not dados.get("titulo") or tipo not in ("livro", "revista"):
            problemas.append(f"{arquivo.name}: sem título ou sem tipo (livro/revista), ficou de fora")
            continue
        item = {"id": arquivo.stem}
        for campo in CAMPOS_PUBLICACOES:
            item[campo] = str(dados.get(campo) or "").strip()
        item["capa"] = caminho_relativo(item["capa"])
        item["link"] = caminho_relativo(item["link"])
        assuntos = dados.get("assuntos")
        item["assuntos"] = [str(a) for a in assuntos if str(a).strip()] if isinstance(assuntos, list) else []
        item["descricao"] = texto_simples(corpo)
        grupos["livros" if tipo == "livro" else "revistas"].append(item)

    for lista in grupos.values():
        lista.sort(key=lambda p: (p["data"] or p["ano"], p["titulo"]), reverse=True)
    SAIDA_PUBLICACOES.write_text(json.dumps(grupos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(grupos['livros'])} livros e {len(grupos['revistas'])} revistas em {SAIDA_PUBLICACOES.relative_to(RAIZ)}")
    return problemas


def capitulos(corpo):
    """Títulos dos capítulos: cada linha "## Título" do texto."""
    return [texto_simples(m.group(1)) for m in re.finditer(r"^##\s+(.+?)\s*$", corpo, flags=re.M)]


def gerar_dossies():
    """Grava dados/dossies.json e devolve a lista de avisos."""
    dossies, problemas = [], []
    for arquivo in sorted(PASTA_DOSSIES.glob("*.md")) if PASTA_DOSSIES.exists() else []:
        try:
            dados, corpo = cabecalho.ler(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            problemas.append(f"{arquivo.name}: arquivo inválido ({erro})")
            continue
        if not dados.get("titulo") or not dados.get("data"):
            problemas.append(f"{arquivo.name}: sem título ou sem data, ficou de fora")
            continue
        item = {"id": arquivo.stem}
        for campo in CAMPOS_DOSSIES:
            item[campo] = str(dados.get(campo) or "").strip()
        item["capa"] = caminho_relativo(item["capa"])
        tags = dados.get("tags")
        tags = tags if isinstance(tags, list) else ([tags] if tags else [])
        item["tags"] = [limpar_tag(t) for t in tags if str(t).strip()]
        item["destaque"] = dados.get("destaque") is True
        item["capitulos"] = capitulos(corpo)
        # PDF: só entra no índice se foi gerado depois da última mudança do texto
        pdf = PASTA_PDF_DOSSIES / f"{arquivo.stem}.pdf"
        item["pdf"] = f"arquivos/dossies/{pdf.name}" if pdf.exists() and pdf.stat().st_mtime >= arquivo.stat().st_mtime else ""
        dossies.append(item)

    dossies.sort(key=lambda d: d["data"], reverse=True)
    SAIDA_DOSSIES.write_text(json.dumps(dossies, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(dossies)} dossiês em {SAIDA_DOSSIES.relative_to(RAIZ)}")
    return problemas


# Plataforma pelo endereço do vídeo, quando o arquivo não diz qual é (a mesma regra de admin/editor.js e curtos.html)
PLATAFORMAS = (
    (r"(^|\.)(youtube\.com|youtu\.be)$", "YouTube"),
    (r"(^|\.)tiktok\.com$", "TikTok"),
    (r"(^|\.)(instagram\.com|instagr\.am)$", "Instagram"),
    (r"(^|\.)(kwai\.com|kw\.ai)$", "Kwai"),
    (r"(^|\.)(x\.com|twitter\.com)$", "X"),
    (r"(^|\.)(facebook\.com|fb\.watch)$", "Facebook"),
    (r"(^|\.)threads\.(net|com)$", "Threads"),
    (r"(^|\.)bsky\.app$", "Bluesky"),
)


def plataforma_do_link(link):
    m = re.match(r"^https?://([^/:?#]+)", link, re.I)
    host = m.group(1).lower().removeprefix("www.") if m else ""
    return next((nome for padrao, nome in PLATAFORMAS if re.search(padrao, host)), "Outra")


def gerar_curtos():
    """Grava dados/curtos.json e devolve a lista de avisos."""
    curtos, problemas = [], []
    for arquivo in sorted(PASTA_CURTOS.glob("*.md")) if PASTA_CURTOS.exists() else []:
        try:
            dados, corpo = cabecalho.ler(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            problemas.append(f"{arquivo.name}: arquivo inválido ({erro})")
            continue
        link = str(dados.get("link") or "").strip()
        if not dados.get("titulo") or not re.match(r"^https?://", link, re.I):
            problemas.append(f"{arquivo.name}: sem título ou sem link, ficou de fora")
            continue
        item = {"id": arquivo.stem}
        for campo in CAMPOS_CURTOS:
            item[campo] = str(dados.get(campo) or "").strip()
        item["plataforma"] = item["plataforma"] or plataforma_do_link(link)
        item["capa"] = caminho_relativo(item["capa"])
        tags = dados.get("tags")
        tags = tags if isinstance(tags, list) else ([tags] if tags else [])
        item["tags"] = [limpar_tag(t) for t in tags if str(t).strip()]
        item["descricao"] = texto_simples(corpo)
        curtos.append(item)

    curtos.sort(key=lambda c: (c["data"], c["titulo"]), reverse=True)
    SAIDA_CURTOS.write_text(json.dumps(curtos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(curtos)} vídeos curtos em {SAIDA_CURTOS.relative_to(RAIZ)}")
    return problemas


def lista_de_textos(valor):
    """Lista do cabeçalho (ou um valor só) como lista de textos sem espaços sobrando."""
    valor = valor if isinstance(valor, list) else ([valor] if valor else [])
    return [str(v).strip() for v in valor if str(v).strip()]


def gerar_metadossies():
    """Grava dados/metadossies.json e devolve a lista de avisos."""
    metas, problemas = [], []
    dossies = {}
    for arquivo in sorted(PASTA_DOSSIES.glob("*.md")) if PASTA_DOSSIES.exists() else []:
        with contextlib.suppress(OSError, ValueError):
            dados, corpo = cabecalho.ler(arquivo.read_text(encoding="utf-8"))
            dossies[arquivo.stem] = {"titulo": str(dados.get("titulo") or arquivo.stem), "capitulos": len(capitulos(corpo)),
                                    "modificado": arquivo.stat().st_mtime}
    for arquivo in sorted(PASTA_METADOSSIES.glob("*.md")) if PASTA_METADOSSIES.exists() else []:
        try:
            dados, _ = cabecalho.ler(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            problemas.append(f"{arquivo.name}: arquivo inválido ({erro})")
            continue
        if not dados.get("titulo") or not dados.get("data"):
            problemas.append(f"{arquivo.name}: sem título ou sem data, ficou de fora")
            continue
        ids = lista_de_textos(dados.get("dossies"))
        faltam = [i for i in ids if i not in dossies]
        if faltam:
            problemas.append(f"{arquivo.name}: dossiê(s) que não existem mais, ignorados: {', '.join(faltam)}")
        partes = [{"id": i, "titulo": dossies[i]["titulo"], "capitulos": dossies[i]["capitulos"]} for i in ids if i in dossies]
        if not partes:
            problemas.append(f"{arquivo.name}: nenhum dossiê válido, ficou de fora")
            continue
        item = {"id": arquivo.stem}
        for campo in CAMPOS_DOSSIES:
            item[campo] = str(dados.get(campo) or "").strip()
        item["capa"] = caminho_relativo(item["capa"])
        item["tags"] = [limpar_tag(t) for t in lista_de_textos(dados.get("tags"))]
        item["destaque"] = dados.get("destaque") is True
        item["dossies"] = partes
        item["capitulos"] = sum(p["capitulos"] for p in partes)
        # PDF em dia: gerado depois da última mudança do meta-dossiê e de cada dossiê que ele junta
        pdf = PASTA_PDF_METADOSSIES / f"{arquivo.stem}.pdf"
        ultima = max([arquivo.stat().st_mtime] + [dossies[p["id"]]["modificado"] for p in partes])
        item["pdf"] = f"arquivos/metadossies/{pdf.name}" if pdf.exists() and pdf.stat().st_mtime >= ultima else ""
        metas.append(item)

    metas.sort(key=lambda d: d["data"], reverse=True)
    SAIDA_METADOSSIES.write_text(json.dumps(metas, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(metas)} meta-dossiês em {SAIDA_METADOSSIES.relative_to(RAIZ)}")
    return problemas


def gerar_casos():
    """Grava dados/casos.json e devolve a lista de avisos."""
    casos, problemas = [], []
    for arquivo in sorted(PASTA_CASOS.glob("*.md")) if PASTA_CASOS.exists() else []:
        try:
            dados, corpo = cabecalho.ler(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            problemas.append(f"{arquivo.name}: arquivo inválido ({erro})")
            continue
        if not dados.get("titulo") or dados.get("status") not in STATUS_CASO:
            problemas.append(f"{arquivo.name}: sem título ou sem situação válida, ficou de fora")
            continue
        item = {"id": arquivo.stem}
        for campo in ("titulo", "status", "aberto", "atualizado", "etapa"):
            item[campo] = str(dados.get(campo) or "").strip()
        item["atualizado"] = item["atualizado"] or item["aberto"]
        item["envolvidos"] = lista_de_textos(dados.get("envolvidos"))
        item["tags"] = [limpar_tag(t) for t in lista_de_textos(dados.get("tags"))]
        documentos = dados.get("documentos") if isinstance(dados.get("documentos"), list) else []
        item["documentos"] = [{"titulo": str(d.get("titulo") or d.get("link") or "").strip(), "link": caminho_relativo(str(d.get("link") or ""))}
                              for d in documentos if isinstance(d, dict) and (d.get("titulo") or d.get("link"))]
        item["resumo"] = texto_simples(corpo)
        casos.append(item)

    casos.sort(key=lambda k: (k["atualizado"], k["titulo"]), reverse=True)
    SAIDA_CASOS.write_text(json.dumps(casos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(casos)} casos em {SAIDA_CASOS.relative_to(RAIZ)}")
    return problemas


if __name__ == "__main__":
    main()
