"""Lê uma consulta pública do e-Cidadania (Senado Federal).

O e-Cidadania não tem uma API pública para as consultas; os dados vêm da própria página da matéria,
https://www12.senado.leg.br/ecidadania/visualizacaomateria?id=<número>.

Uso:  python scripts/ecidadania.py 173618
      python scripts/ecidadania.py "https://www12.senado.leg.br/ecidadania/visualizacaomateria?id=173618"
"""
import html
import json
import re
import sys
import urllib.error
import urllib.request

ENDERECO = "https://www12.senado.leg.br/ecidadania/visualizacaomateria?id={}"
TRAMITACAO = "https://www25.senado.leg.br/web/atividade/materias/-/materia/{}"
AGENTE = "Mozilla/5.0 (compatible; TempoContinuum/1.0; editor local)"


class ErroConsulta(Exception):
    pass


def numero_da_consulta(entrada):
    """Aceita o número (173618) ou um link do e-Cidadania ou da página da matéria no Senado."""
    t = str(entrada or "").strip()
    m = re.search(r"[?&]id=(\d{1,8})\b", t) or re.search(r"/materia/(\d{1,8})\b", t) or re.fullmatch(r"(\d{1,8})", t)
    if not m:
        raise ErroConsulta("cole o link da consulta no e-Cidadania (…visualizacaomateria?id=…) ou só o número dela")
    return int(m.group(1))


def _texto(trecho):
    t = re.sub(r"<br\s*/?>", "\n", trecho or "", flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return "\n".join(" ".join(l.split()) for l in t.split("\n")).strip()


def _achar(padrao, pagina):
    m = re.search(padrao, pagina, re.S | re.I)
    return _texto(m.group(1)) if m else ""


def _numero(t):
    t = re.sub(r"[^\d]", "", t or "")
    return int(t) if t else 0


def ler_pagina(pagina, numero):
    pagina = re.sub(r"<!--.*?-->", "", pagina, flags=re.S)   # a página tem trechos antigos comentados
    if 'id="materiaId"' not in pagina:
        raise ErroConsulta(f"não achei a consulta {numero} no e-Cidadania")
    ident = re.search(r'class="materia-identificacao".*?<header>(.*?)</header>.*?<span>(.*?)</span>', pagina, re.S)
    apurado = _achar(r'id="msg-contabilizacao-voto"[^>]*>(.*?)</div>', pagina)
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})\s+(\d{2}:\d{2})(?::\d{2})?", apurado)
    return {
        "ecidadania_id": numero,
        "identificacao": _texto(ident.group(1)) if ident else "",
        "sigla": _texto(ident.group(2)) if ident else "",
        "autoria": _achar(r"<b>\s*Autoria:\s*</b>\s*<span[^>]*>(.*?)</span>", pagina),
        "ementa": _achar(r"<b>\s*Ementa:\s*</b>\s*<span[^>]*>(.*?)</span>", pagina),
        "explicacao": _achar(r"<b>\s*O que é\s*</b>\s*</h5>\s*<div[^>]*>(.*?)</div>", pagina),
        "votos_sim": _numero(_achar(r'class="contabilizacao-favor"[^>]*>(.*?)<', pagina)),
        "votos_nao": _numero(_achar(r'class="contabilizacao-contra"[^>]*>(.*?)<', pagina)),
        "apurado_em": f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{m.group(4)}:00" if m else "",
        "link": ENDERECO.format(numero),
        "tramitacao": TRAMITACAO.format(numero),
    }


def buscar(entrada, tempo=20):
    numero = numero_da_consulta(entrada)
    pedido = urllib.request.Request(ENDERECO.format(numero), headers={"User-Agent": AGENTE, "Accept-Language": "pt-BR"})
    try:
        with urllib.request.urlopen(pedido, timeout=tempo) as r:
            pagina = r.read(3 * 1024 * 1024).decode(r.headers.get_content_charset() or "utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise ErroConsulta(f"o e-Cidadania respondeu com erro {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ErroConsulta("não consegui abrir o e-Cidadania (sem internet ou o site do Senado está fora do ar)") from e
    return ler_pagina(pagina, numero)


if __name__ == "__main__":
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8")
    try:
        print(json.dumps(buscar(sys.argv[1] if len(sys.argv) > 1 else ""), ensure_ascii=False, indent=1))
    except ErroConsulta as e:
        sys.exit(f"Erro: {e}")
