"""Coleta os contatos dos deputados estaduais (e distritais do DF) nos sites oficiais das 27 Assembleias.

Não existe uma base nacional com esses contatos: cada Assembleia publica os seus do seu jeito. MG e SP têm
dados abertos estruturados; nas outras, o script lê a página de cada deputado no site oficial e tira dela
e-mail, telefone, gabinete, redes sociais e foto. O que se repete em quase todos os perfis de um mesmo estado
(telefone geral, e-mail da ouvidoria, redes da própria Assembleia) é descartado, porque não é do deputado.

Uso:  python scripts/estaduais.py            (todos os estados; quem chama é scripts/parlamentares.py)
      python scripts/estaduais.py SP RJ      (só alguns, para testar; mostra o resultado e não grava nada)
"""
import gzip
import html
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

AGENTE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

# Cadeiras de cada Assembleia (Constituição, art. 27). Serve para avisar quando a coleta veio incompleta.
CADEIRAS = {"AC": 24, "AL": 27, "AM": 24, "AP": 24, "BA": 63, "CE": 46, "DF": 24, "ES": 30, "GO": 41, "MA": 42,
            "MG": 77, "MS": 24, "MT": 24, "PA": 41, "PB": 36, "PE": 49, "PI": 30, "PR": 54, "RJ": 70, "RN": 24,
            "RO": 24, "RR": 24, "RS": 55, "SC": 40, "SE": 24, "SP": 94, "TO": 24}
NOMES_CASAS = {"GO": "Assembleia Legislativa de Goiás (Alego)"}
# Observações que aparecem na página, por estado
AVISOS = {
    "AL": "O cadastro oficial (SAPL) da Assembleia lista mais parlamentares com mandato ativo do que as 27 cadeiras; "
          "alguns podem estar licenciados.",
    "MS": "A Assembleia publica telefone e e-mail de cada gabinete, mas não o partido.",
    "TO": "O cadastro oficial da Assembleia não informa o partido atual.",
    "MT": "O site da Assembleia não publica e-mail nem telefone dos gabinetes; use a página oficial e as redes.",
}
DDD = {"AC": "68", "AL": "82", "AM": "92", "AP": "96", "BA": "71", "CE": "85", "DF": "61", "ES": "27", "GO": "62",
       "MA": "98", "MG": "31", "MS": "67", "MT": "65", "PA": "91", "PB": "83", "PE": "81", "PI": "86", "PR": "41",
       "RJ": "21", "RN": "84", "RO": "69", "RR": "95", "RS": "51", "SC": "48", "SE": "79", "SP": "11", "TO": "63"}
PARTIDOS = ["PT", "PL", "UNIÃO", "UNIAO", "UNIÃO BRASIL", "PSD", "MDB", "PP", "REPUBLICANOS", "PSB", "PDT", "PSDB",
            "PSOL", "PODEMOS", "PODE", "AVANTE", "PCdoB", "PC do B", "PV", "CIDADANIA", "SOLIDARIEDADE", "NOVO",
            "PRD", "REDE", "AGIR", "DC", "MOBILIZA", "PMB", "PRTB", "PSC", "PTB", "PROS", "PATRIOTA", "PMN", "PTC",
            "UP", "PCB", "PSTU", "PCO", "PSDB/CIDADANIA"]
PARTIDO_NOMES = [
    ("partido da social democracia brasileira", "PSDB"), ("partido socialista brasileiro", "PSB"),
    ("partido dos trabalhadores", "PT"), ("partido liberal", "PL"), ("partido social democrático", "PSD"),
    ("partido social democratico", "PSD"), ("movimento democrático brasileiro", "MDB"),
    ("movimento democratico brasileiro", "MDB"), ("partido progressistas", "PP"), ("progressistas", "PP"),
    ("partido democrático trabalhista", "PDT"), ("partido democratico trabalhista", "PDT"),
    ("partido socialismo e liberdade", "PSOL"), ("partido comunista do brasil", "PCdoB"),
    ("partido verde", "PV"), ("partido renovação democrática", "PRD"), ("partido renovacao democratica", "PRD"),
    ("rede sustentabilidade", "REDE"), ("partido novo", "NOVO"), ("união brasil", "UNIÃO"), ("uniao brasil", "UNIÃO"),
    ("republicanos", "REPUBLICANOS"), ("podemos", "PODEMOS"), ("avante", "AVANTE"), ("cidadania", "CIDADANIA"),
    ("solidariedade", "SOLIDARIEDADE"), ("mobiliza", "MOBILIZA"), ("agir", "AGIR"), ("democracia cristã", "DC"),
    ("democracia crista", "DC"), ("partido da mulher brasileira", "PMB"),
    ("partido renovador trabalhista brasileiro", "PRTB"), ("partido trabalhista brasileiro", "PTB"),
]
SIGLAS = {"PT", "PL", "PSD", "MDB", "PP", "PSB", "PDT", "PSDB", "PSOL", "PV", "PRD", "REDE", "NOVO", "UNIÃO", "UNIAO",
          "REPUBLICANOS", "REP", "PODEMOS", "PODE", "AVANTE", "CIDADANIA", "SOLIDARIEDADE", "MOBILIZA", "AGIR", "DC",
          "PMB", "PRTB", "PTB", "PCDOB", "PC DO B", "PSC", "PROS", "PATRIOTA", "PMN", "PTC", "UP", "PCB"}


def partido_em(txt):
    """Acha um partido (por extenso ou sigla) num texto curto. Devolve (sigla, texto sem o partido)."""
    baixo = (txt or "").lower()
    for nome, sigla in PARTIDO_NOMES:
        i = baixo.find(nome)
        if i >= 0:
            return sigla, (txt[:i] + txt[i + len(nome):]).strip()
    for m in re.finditer(r"(?<![\wÀ-ú])(PC do B|PCdoB|[A-ZÃ]{2,13})(?![\wÀ-ú])", txt or ""):
        if m.group(1).upper() in SIGLAS:
            return norm_partido(m.group(1)), (txt[:m.start()] + txt[m.end():]).strip()
    return "", txt or ""


REDES = re.compile(r"https?://(?:www\.|m\.|pt-br\.|web\.)?(?:instagram\.com|facebook\.com|fb\.com|twitter\.com|x\.com|"
                   r"youtube\.com|youtu\.be|tiktok\.com|threads\.net|threads\.com|linkedin\.com|kwai\.com|bsky\.app|"
                   r"t\.me|flickr\.com)/[^\s\"'<>)]+", re.I)


class Falha(Exception):
    pass


# ---------------------------------------------------------------- utilidades

def baixar(url, tentativas=3, dados=None, cabecalhos=None):
    h = {"User-Agent": AGENTE, "Accept-Language": "pt-BR,pt;q=0.9", "Accept": "*/*"}
    h.update(cabecalhos or {})
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, data=dados, headers=h)
            with urllib.request.urlopen(req, timeout=45) as r:
                b = r.read()
                cs = r.headers.get_content_charset()
            if b[:2] == b"\x1f\x8b":  # alguns sites mandam gzip mesmo sem pedirmos
                b = gzip.decompress(b)
            if cs:
                try:
                    return b.decode(cs)
                except (LookupError, UnicodeDecodeError):
                    pass
            try:
                return b.decode("utf-8")
            except UnicodeDecodeError:
                return b.decode("latin-1")
        except Exception as e:
            if i == tentativas - 1:
                raise Falha(f"{url}: {e}")
            time.sleep(2 * (i + 1))


def texto(trecho):
    t = re.sub(r"<(script|style|noscript)[\s\S]*?</\1>", " ", trecho or "", flags=re.I)
    t = re.sub(r"<br\s*/?>|</(p|div|li|tr|h\d|dd|dt|td)>", "\n", t, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return "\n".join(" ".join(l.split()) for l in t.split("\n") if l.strip())


def limpo(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))).split())


def absoluto(base, href):
    return urllib.parse.urljoin(base, html.unescape(href.strip()))


def links(pagina, base, padrao):
    vistos, saida = set(), []
    for h in re.findall(r'href\s*=\s*["\']([^"\']+)["\']', pagina, re.I):
        u = absoluto(base, h).split("#")[0]
        if urllib.parse.urlsplit(u).scheme not in ("http", "https"):
            continue
        if urllib.parse.urlsplit(u).hostname != urllib.parse.urlsplit(base).hostname:
            continue
        if re.search(padrao, u) and u not in vistos:
            vistos.add(u)
            saida.append(u)
    return saida


CARGOS = r"(1º|2º|3º|4º|1ª|2ª|3ª|4ª)?\s*(Presidente|Vice-?\s*[Pp]residente|Secretári[oa]|Corregedor[a]?|Ouvidor[a]?|Líder[^,]*?|Procurador[a]?)"


def limpar_nome(s):
    s = limpo(s)
    s = re.sub(r"^(Foto\s+d[oa]\s+)?(Deputad[oa](\(a\))?\s*(Estadual|Distrital)?|Dep\.|Dept[ºo]\.?)\s+", "", s, flags=re.I)
    s = re.sub(CARGOS, " ", s)
    s = re.sub(r"\s+Deputad[oa](\s+(Estadual|Distrital))?\s*$", "", s, flags=re.I)
    s = re.sub(r"\(\s*[A-Za-zÀ-ú ]{0,20}\s*\)\s*$", "", s)
    s = re.sub(r"\(?\d{2}\)?\s*\d{4,5}[-.\s]?\d{4}.*$|\S+@\S+.*$", "", s)
    return " ".join(s.split()).strip(" -–|,")


def links_com_nome(pagina, base, padrao, outro_host=None):
    """{url do perfil: (nome, partido)} tirados do link da lista (texto, alt ou title da foto)."""
    saida = {}
    hosts = {urllib.parse.urlsplit(base).hostname, outro_host}
    for m in re.finditer(r"""<a\b([^>]*?)href\s*=\s*["']([^"']+)["']([^>]*)>([\s\S]*?)</a>""", pagina, re.I):
        u = absoluto(base, m.group(2)).split("#")[0]
        sp = urllib.parse.urlsplit(u)
        if sp.scheme not in ("http", "https") or sp.hostname not in hosts or not re.search(padrao, u):
            continue
        dentro = m.group(4)
        alts = [html.unescape(x) for x in re.findall(r"""\b(?:alt|title)\s*=\s*["']([^"']+)""", m.group(1) + m.group(3) + dentro)]
        corpo = limpo(dentro)
        partido, resto = partido_em(corpo)
        candidatos = [limpar_nome(a) for a in alts] + [limpar_nome(resto)]
        candidatos = [c for c in candidatos if 2 < len(c) < 60 and not re.search(r"veja mais|saiba mais|perfil|leia", c, re.I)]
        nome = min(candidatos, key=len) if candidatos else ""
        antigo = saida.get(u, ("", ""))
        saida[u] = (antigo[0] or nome, antigo[1] or partido)
    return saida


def meta(pagina, prop):
    m = re.search(r'<meta[^>]+(?:property|name)=["\']' + re.escape(prop) + r'["\'][^>]*content=["\']([^"\']*)', pagina, re.I) \
        or re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']' + re.escape(prop) + '["\']', pagina, re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def emails(pagina):
    t = html.unescape(pagina).replace("[at]", "@").replace("(at)", "@")
    achados = re.findall(r"(?<![\w.@-])([\w.+-]+@[\w-]+(?:\.[\w-]+)*\.(?:br|com|net|org))(?![\w-])", t, re.I)
    saida = []
    for e in achados:
        e = e.strip(".").lower()
        if re.search(r"\.(png|jpe?g|gif|svg|webp)$", e) or e in saida:
            continue
        saida.append(e)
    return saida


def telefones(txt, uf):
    """Telefones com DDD do estado (ou sem DDD, assumindo o do estado)."""
    saida = []
    for m in re.finditer(r"(?<![\d/])(?:\+?55\s*)?(?:\(\s*0?(\d{2})\s*\)|\b0?(\d{2}))?[\s.-]*(9?\d{4})[\s.-](\d{4})(?!\d)", txt):
        ddd = m.group(1) or m.group(2)
        if ddd is None:
            if len(m.group(3)) != 4:
                continue
            ddd = DDD[uf]
        if not (11 <= int(ddd) <= 99) or ddd[1] == "0":
            continue
        if re.fullmatch(r"(19|20)\d\d", m.group(3)) and re.fullmatch(r"(19|20)\d\d", m.group(4)):
            continue  # "2019-2023" é intervalo de anos, não telefone
        if len(set(m.group(3) + m.group(4))) <= 2:
            continue  # 3333-3333 e parecidos
        if ddd != DDD[uf] and ddd not in ("61",):
            # DDD de outra região: aceita só se o número veio escrito com DDD entre parênteses
            if not m.group(1):
                continue
        num = f"({ddd}) {m.group(3)}-{m.group(4)}"
        if num not in saida:
            saida.append(num)
    return saida


def telefones_campo(valor, uf):
    """Campo que só tem telefones ("32144550 / (83) 3214-4551"): aceita números sem hífen."""
    saida = []
    for parte in re.split(r"[/;,]|\s+e\s+", valor or ""):
        dig = re.sub(r"\D", "", parte)
        if dig.startswith("0"):
            dig = dig[1:]
        if len(dig) in (8, 9):
            dig = DDD[uf] + dig
        if len(dig) in (10, 11) and dig[0] != "0":
            num = f"({dig[:2]}) {dig[2:-4]}-{dig[-4:]}"
            if num not in saida:
                saida.append(num)
    return saida


def redes(pagina):
    saida = []
    for u in REDES.findall(html.unescape(pagina)):
        u = u.rstrip(".,;/")
        if re.search(r"/(sharer|share|intent|plugins|dialog|embed|hashtag|explore|watch\?|p/|reel/|status/|posts/|photo|tr\?)", u, re.I):
            continue
        if re.search(r"(facebook|instagram|twitter|x)\.com/?$", u, re.I):
            continue
        chave = re.sub(r"^https?://(www\.|m\.)?", "", u.lower()).rstrip("/")
        if chave not in [re.sub(r"^https?://(www\.|m\.)?", "", s.lower()).rstrip("/") for s in saida]:
            saida.append(u)
    return saida


def partido_no(txt, nome=None):
    """Partido num perfil: depois de um rótulo ("Partido:", "Filiação partidária:") ou logo depois do nome."""
    for m in re.finditer(r"(?:Partido|Filia[çc][ãa]o partid[áa]ria|Sigla partid[áa]ria|Legenda)\s*[:\-–]\s*", txt, re.I):
        p = partido_em(txt[m.end():m.end() + 45].split("\n")[0])[0]
        if p:
            return p
    if nome:
        ini = 0
        while True:
            i = txt.find(nome, ini)
            if i < 0:
                break
            p, _ = partido_em(txt[i + len(nome):i + len(nome) + 40])
            if p:
                return p
            ini = i + 1
    return ""


def foto_com_nome(pagina, base, nome):
    """Uma <img> cujo alt/title traz o nome do deputado."""
    if not nome:
        return ""
    chave = nome.lower()
    for m in re.finditer(r"<img\b[^>]*>", pagina, re.I):
        tag = m.group(0)
        alt = html.unescape(" ".join(re.findall(r"""\b(?:alt|title)\s*=\s*["']([^"']*)""", tag, re.I))).lower()
        src = re.search(r"""\b(?:data-src|src)\s*=\s*["']([^"']+)""", tag, re.I)
        # alt curto com o nome ("Foto de Fulano", "Dep. Fulano"); legenda longa de notícia não serve
        if src and chave in alt and len(alt) <= len(chave) + 25 and not re.search(r"logo|icon|brasao|banner", src.group(1), re.I):
            return absoluto(base, src.group(1))
    return ""


def norm_partido(s):
    s = " ".join(str(s or "").split()).strip(" -–()").upper()
    s = {"UNIAO": "UNIÃO", "UNIÃO BRASIL": "UNIÃO", "UNIAO BRASIL": "UNIÃO", "PODE": "PODEMOS", "PC DO B": "PCDOB",
         "REP": "REPUBLICANOS", "REPUBLICA": "REPUBLICANOS", "PROGRESSISTAS": "PP", "UB": "UNIÃO",
         "SOLIDARIEDADE": "SOLIDARIEDADE"}.get(s, s)
    if s == "PCDOB":
        return "PCdoB"
    validos = {p.upper() for p in PARTIDOS} | {"UNIÃO", "PCDOB"}
    return s if s in validos else ""


def nome_de_titulo(pagina):
    for bruto in (meta(pagina, "og:title"), (re.search(r"<h1[^>]*>([\s\S]*?)</h1>", pagina, re.I) or [None, ""])[1],
                  (re.search(r"<title[^>]*>([\s\S]*?)</title>", pagina, re.I) or [None, ""])[1]):
        n = limpo(bruto)
        n = re.split(r"\s+[|–—]\s+|\s+-\s+(?=Assembl|ALE|Portal|Câmara|CLDF)", n)[0]
        n = re.sub(r"^(Deputad[oa]s?\s+(Estadual|Distrital)?\s*|Dep\.\s*|Perfil\s*[:-]?\s*)", "", n, flags=re.I).strip(" -|")
        if 2 < len(n) < 60:
            return n
    return ""


def perfis(uf, urls, extrair, trabalhadores=6):
    """Baixa cada perfil e aplica `extrair(url, pagina) -> dict`. Ignora perfis que falham."""
    def um(u):
        try:
            return extrair(u, baixar(u))
        except Falha as e:
            print(f"  [{uf}] aviso: {e}", file=sys.stderr)
            return None
    with ThreadPoolExecutor(max_workers=trabalhadores) as ex:
        return [d for d in ex.map(um, urls) if d]


def generico(uf, nome_rx=None, partido_rx=None, corpo_rx=None, foto_rx=None):
    """Extrator padrão de um perfil: nome, partido, e-mails, telefones, redes e foto.
    `corpo_rx` recorta o trecho da página que é do deputado (para não pegar menus e rodapé)."""
    def extrair(url, pagina, nome_dica="", partido_dica=""):
        corpo = pagina
        if corpo_rx:
            m = re.search(corpo_rx, pagina, re.I)
            if m:
                corpo = m.group(1)
        txt = texto(corpo)
        nome = ""
        if nome_rx:
            m = re.search(nome_rx, pagina, re.I)
            nome = limpar_nome(m.group(1)) if m else ""
        nome = nome or nome_dica or nome_de_titulo(pagina)
        partido = ""
        if partido_rx:
            m = re.search(partido_rx, pagina, re.I)
            partido = (partido_em(limpo(m.group(1)))[0] or norm_partido(limpo(m.group(1)))) if m else ""
        partido = partido or partido_dica or partido_no(txt, nome)
        foto = ""
        if foto_rx:
            m = re.search(foto_rx, pagina, re.I)
            foto = absoluto(url, m.group(1)) if m else ""
        foto = foto or foto_com_nome(corpo, url, nome) or meta(pagina, "og:image")
        endereco = ""
        m = re.search(r"(?:Gabinete|Endereço do gabinete|Localização)\s*:\s*([^\n]{5,160}?)(?=\s*(?:Facebook|Instagram|Telefone|E-?mail|Fone|\n|$))", txt, re.I)
        if m and re.search(r"[A-Za-zÀ-ú]{3}", m.group(1)) and not re.search(r"@", m.group(1)):
            endereco = m.group(1).strip(" -–,")
        return {"nome": nome, "partido": partido, "emails": emails(corpo), "telefones": telefones(txt, uf),
                "redes": redes(corpo), "foto": foto, "pagina": url, "endereco": endereco}
    return extrair


def depurar(uf, itens):
    """Tira dos perfis o que se repete em quase todos (dado da Assembleia, não do deputado)."""
    n = len(itens)
    if n < 4:
        return itens
    limite = max(3, n * 0.4)
    for campo in ("emails", "telefones", "redes"):
        cont = Counter(v for d in itens for v in set(d.get(campo) or []))
        comuns = {v for v, c in cont.items() if c >= limite}
        for d in itens:
            d[campo] = [v for v in (d.get(campo) or []) if v not in comuns]
    fotos = Counter(d.get("foto") for d in itens if d.get("foto"))
    for d in itens:
        if d.get("foto") and fotos[d["foto"]] >= limite:
            d["foto"] = ""
    return itens


MINUSCULAS = {"da", "de", "do", "das", "dos", "e"}


def capitalizar(nome):
    """'ALAN LOPES' -> 'Alan Lopes' (só quando o site escreve tudo em maiúsculas)."""
    if not nome or nome != nome.upper():
        return nome
    return " ".join(w.lower() if w.lower() in MINUSCULAS and i else w.capitalize() for i, w in enumerate(nome.lower().split()))


def montar(uf, d, assembleia):
    d["nome"] = capitalizar(d.get("nome"))
    tels = []
    for t in d.get("telefones") or []:
        if t not in tels:
            tels.append(t)
    mails = [e for e in (d.get("emails") or []) if not re.match(r"(ouvidoria|imprensa|comunicacao|protocolo|"
                                                                   r"contato|faleconosco|webmaster|ti|suporte|atendimento)@", e)]
    return {
        "casa": "estadual",
        "id": f"{uf.lower()}-{re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFD', d.get('nome') or '').encode('ascii', 'ignore').decode().lower()).strip('-')}",
        "nome": d.get("nome") or "",
        "partido": d.get("partido") or "",
        "uf": uf,
        "foto": d.get("foto") or "",
        "email": mails[0] if mails else "",
        "emails_extras": mails[1:3],
        "telefones": tels[:4],
        "endereco": d.get("endereco") or "",
        "pagina": d.get("pagina") or "",
        "redes": (d.get("redes") or [])[:6],
        "assembleia": assembleia,
    }


# ---------------------------------------------------------------- estados com dados abertos

def sp():
    raiz = ET.fromstring(baixar("https://www.al.sp.gov.br/repositorioDados/deputados/deputados.xml").encode("utf-8"))
    saida = []
    for d in raiz.findall("Deputado"):
        if (d.findtext("Situacao") or "") != "EXE":
            continue
        tels = []
        bruto = d.findtext("Telefone") or ""
        partes = re.split(r"\s*[/;,e]\s*", bruto)
        base = ""
        for p in partes:
            dig = re.sub(r"\D", "", p)
            if len(dig) >= 8:
                base = dig[-8:]
                tels.append(f"(11) {base[:4]}-{base[4:]}")
            elif base and 2 <= len(dig) <= 4:
                b = base[:8 - len(dig)] + dig
                tels.append(f"(11) {b[:4]}-{b[4:]}")
        sala, andar = d.findtext("Sala") or "", (d.findtext("Andar") or "").strip()
        if andar and "andar" not in andar.lower():
            andar += " andar"
        end = "Palácio 9 de Julho, " + ", ".join(x for x in (andar, f"sala {sala}" if sala else "") if x) if (sala or andar) else ""
        saida.append({"nome": d.findtext("NomeParlamentar") or "", "partido": norm_partido(d.findtext("Partido")) or (d.findtext("Partido") or ""),
                      "emails": [d.findtext("Email")] if d.findtext("Email") else [], "telefones": tels,
                      "endereco": (end + " — São Paulo/SP") if end else "",
                      "pagina": f"https://www.al.sp.gov.br/deputado/?matricula={d.findtext('Matricula')}",
                      "foto": "",
                      "redes": []})
    return saida


def mg():
    base = "https://dadosabertos.almg.gov.br/api/v2/deputados"
    lista = json.loads(baixar(f"{base}/em_exercicio?formato=json"))["list"]

    def um(d):
        det = json.loads(baixar(f"{base}/{d['id']}?formato=json"))["deputado"]
        mails = []
        for e in det.get("emails") or []:
            end = (e.get("endereco") or "").strip()
            if end:
                mails.append(end if "@" in end else end + "@almg.gov.br")
        tels, end = [], ""
        for e in det.get("enderecos") or []:
            if (e.get("descTipo") or "").lower().startswith("gabinete") and not end:
                end = ", ".join(x for x in (e.get("complemento"), f"{e.get('logradouro', '')}, {e.get('numero', '')}".strip(", "))
                                if x) + " — Belo Horizonte/MG"
            for t in e.get("telefones") or []:
                if t.get("fax") == "S":
                    continue
                n = re.sub(r"\D", "", t.get("numero") or "")
                if len(n) >= 8:
                    tels.append(f"({t.get('ddd') or '31'}) {n[:-4]}-{n[-4:]}")
        return {"nome": det.get("nome") or d["nome"], "partido": norm_partido(det.get("partido")) or det.get("partido") or "",
                "emails": mails, "telefones": tels, "endereco": end,
                "pagina": f"https://www.almg.gov.br/deputados/conheca_deputados/deputados-info.html?idDep={d['id']}",
                "foto": f"https://www.almg.gov.br/export/sites/portal/a-assembleia/deputados/fotos/{d['id']}.jpg",
                "redes": [r.get("url") for r in det.get("redesSociais") or [] if r.get("url")]}

    with ThreadPoolExecutor(max_workers=6) as ex:
        return list(ex.map(um, lista))


# ---------------------------------------------------------------- estados lidos dos sites

def ba():
    u = "https://www.al.ba.gov.br/deputados/contatos-deputados"
    pag = baixar(u)
    saida = []
    for linha in re.findall(r'<tr class="table-itens">([\s\S]*?)</tr>', pag):
        cel = re.findall(r"<td[^>]*>([\s\S]*?)</td>", linha)
        if len(cel) < 6:
            continue
        end = limpo(cel[3])
        saida.append({"nome": limpo(cel[0]), "partido": norm_partido(limpo(cel[2])) or limpo(cel[2]),
                      "emails": emails(cel[4]), "telefones": [],
                      "endereco": (f"Assembleia Legislativa da Bahia, {end} — Salvador/BA") if end else "",
                      "pagina": "https://www.al.ba.gov.br/deputados/deputados-estaduais", "foto": "", "redes": redes(cel[5])})
    return saida


def por_perfis(uf, cfg):
    """Estado cujo site tem uma lista de deputados com um link para o perfil de cada um.
    cfg: lista (url ou urls), padrao (regex do link do perfil) e, se preciso, nome_rx, partido_rx,
    corpo_rx (trecho da página que é do deputado) e preparar (função que limpa o HTML da lista)."""
    def fn():
        achados = {}
        listas = cfg["lista"] if isinstance(cfg["lista"], (list, tuple)) else [cfg["lista"]]
        for lu in listas:
            pag = baixar(lu)
            if cfg.get("preparar"):
                pag = cfg["preparar"](pag)
            for u, v in links_com_nome(pag, lu, cfg["padrao"], cfg.get("host_perfil")).items():
                achados.setdefault(u, v)
        if not achados:
            raise Falha(f"nenhum perfil encontrado em {listas[0]}")
        ext = generico(uf, cfg.get("nome_rx"), cfg.get("partido_rx"), cfg.get("corpo_rx"), cfg.get("foto_rx"))
        return perfis(uf, list(achados), lambda u, pag: ext(u, pag, *achados[u]))
    return fn


def _sem_blocos(classe):
    """preparar=...: tira da lista os cartões com essa classe (licenciados, por exemplo)."""
    return lambda pag: re.sub(r'<div[^>]*class="[^"]*\b' + classe + r'\b[^"]*"[\s\S]*?(?=<div[^>]*class="[^"]*deputado_card|</main>)', "", pag)


GENERICOS = {
    "AM": {"casa": "Assembleia Legislativa do Amazonas (Aleam)", "lista": "https://www.aleam.gov.br/deputados/",
           "padrao": r"aleam\.gov\.br/deputados/[a-z0-9-]+/?$"},
    "AP": {"casa": "Assembleia Legislativa do Amapá (Alap)", "lista": "https://www.al.ap.leg.br/",
           "padrao": r"pg=exibir_parlamentar&iddeputado=\d+$"},
    "CE": {"casa": "Assembleia Legislativa do Ceará (Alece)", "lista": "https://www.al.ce.gov.br/deputados",
           "padrao": r"al\.ce\.gov\.br/deputados/(?!mesa-diretora|lideres|bancadas|legislaturas)[a-z0-9-]+$",
           "preparar": _sem_blocos("licenciado")},
    "ES": {"casa": "Assembleia Legislativa do Espírito Santo (Ales)", "lista": "https://www.al.es.gov.br/Deputado/Lista",
           "padrao": r"al\.es\.gov\.br/Deputado/(?!Lista)[A-Za-z0-9]+$"},
    "MA": {"casa": "Assembleia Legislativa do Maranhão (Alema)", "lista": "https://www.al.ma.leg.br/sitealema/deputados/",
           "padrao": r"sitealema/deputado/[a-z0-9-]+/?$"},
    "MT": {"casa": "Assembleia Legislativa de Mato Grosso (ALMT)", "lista": "https://www.al.mt.gov.br/parlamento/deputados",
           "padrao": r"/parlamento/deputados/\d+/perfil$"},
    "PR": {"casa": "Assembleia Legislativa do Paraná (Alep)", "lista": "https://www.assembleia.pr.leg.br/deputados/conheca",
           "padrao": r"/deputados/perfil/[a-z0-9-]+$"},
    "RN": {"casa": "Assembleia Legislativa do Rio Grande do Norte (ALRN)", "lista": "https://www.al.rn.leg.br/",
           "padrao": r"al\.rn\.leg\.br/deputado/\d+/[a-z0-9-]+$"},
    "SC": {"casa": "Assembleia Legislativa de Santa Catarina (Alesc)", "lista": "https://www.alesc.sc.gov.br/",
           "padrao": r"alesc\.sc\.gov\.br/deputado/[a-z0-9-]+/?$"},
    "RJ": {"casa": "Assembleia Legislativa do Rio de Janeiro (Alerj)", "lista": "https://www.alerj.rj.gov.br/Deputados/QuemSao",
           "padrao": r"/Deputados/PerfilDeputado/\d+\?Legislatura=\d+$",
           "partido_rx": r'<div class="partido"><span>([^<]+)</span>', "foto_rx": r'<img src="(/Uploads/PerfilDeputado/Imagem/[^"]+)"'},
    "PE": {"casa": "Assembleia Legislativa de Pernambuco (Alepe)", "lista": "https://www.alepe.pe.gov.br/parlamentares/",
           "padrao": r"alepe\.pe\.gov\.br/parlamentar/[a-z0-9-]+/?$"},
    "SE": {"casa": "Assembleia Legislativa de Sergipe (Alese)", "lista": "https://al.se.leg.br/deputados/",
           "padrao": r"/spl/parlamentar\.aspx\?id=\d+$", "host_perfil": "aleselegis.al.se.leg.br",
           "nome_rx": r'id="nome_parlamentar"[^>]*>([^<]+)<', "foto_rx": r"""src=['"]([^'"]*images/pessoas/[^'"]+)"""},
    "RO": {"casa": "Assembleia Legislativa de Rondônia (ALE-RO)", "lista": "https://www.al.ro.leg.br/deputados/perfil/",
           "padrao": r"/deputados/perfil/[a-z0-9-]+$"},
}


def _sapl_todos(host, caminho):
    """Todas as páginas de um endpoint da API do SAPL."""
    url, saida = f"https://{host}{caminho}{'&' if '?' in caminho else '?'}page_size=100", []
    pagina = 1
    while url and pagina <= 60:
        d = json.loads(baixar(url, cabecalhos={"Accept": "application/json"}))
        saida += d.get("results") or []
        prox = (d.get("pagination") or {}).get("next_page")
        url = f"https://{host}{caminho}{'&' if '?' in caminho else '?'}page_size=100&page={prox}" if prox else None
        pagina += 1
    return saida


def sapl(host, uf, site=None):
    """Assembleias que usam o SAPL (Interlegis): API pública e igual em todas.
    Pega a legislatura atual, os mandatos vigentes hoje, os dados de cada parlamentar e a filiação atual."""
    def fn():
        hoje = time.strftime("%Y-%m-%d")
        legs = _sapl_todos(host, "/api/parlamentares/legislatura/")
        atual = [l for l in legs if (l.get("data_inicio") or "") <= hoje <= (l.get("data_fim") or "9999")]
        if not atual:
            raise Falha(f"{host}: legislatura atual não encontrada")
        leg = atual[0]["id"]
        mandatos = [m for m in _sapl_todos(host, f"/api/parlamentares/mandato/?legislatura={leg}")
                    if m.get("legislatura") == leg and (m.get("data_inicio_mandato") or "") <= hoje
                    and (m.get("data_fim_mandato") or "9999") >= hoje]
        # Em exercício = tem mandato vigente nesta legislatura E está marcado como ativo no cadastro
        pessoas = {p["id"]: p for p in _sapl_todos(host, "/api/parlamentares/parlamentar/") if p.get("ativo")}
        ids = sorted({m["parlamentar"] for m in mandatos} & set(pessoas))
        siglas = {}
        try:
            for pt in _sapl_todos(host, "/api/parlamentares/partido/"):
                siglas[pt["id"]] = pt.get("sigla") or ""
        except Falha:
            pass
        filiacoes = {}
        for f in _sapl_todos(host, "/api/parlamentares/filiacao/"):
            if f.get("data_desfiliacao") or f.get("parlamentar") not in ids:
                continue
            if (f.get("data") or "") >= filiacoes.get(f["parlamentar"], ("", ""))[0]:
                partes = (f.get("__str__") or "").split(" - ")
                sigla = siglas.get(f.get("partido")) or (partes[1].strip() if len(partes) > 1 else "")
                filiacoes[f["parlamentar"]] = (f.get("data") or "", sigla)

        saida = []
        for pid in ids:
            p = pessoas[pid]
            tels = []
            for campo in ("telefone", "telefone_celular"):
                tels += [t for t in telefones_campo(p.get(campo), uf) if t not in tels]
            gab = (p.get("numero_gab_parlamentar") or "").strip()
            if re.fullmatch(r"[\d\s().\-/]{8,}", gab):  # há Assembleias que põem o telefone aqui
                tels += [t for t in telefones_campo(gab, uf) if t not in tels]
                gab = ""
            foto = p.get("fotografia") or ""
            if foto and not foto.startswith("http"):
                foto = f"https://{host}{foto}"
            foto = re.sub(r"^http://", "https://", foto)
            redes_p = [u for u in re.split(r"[\s,;]+", p.get("endereco_web") or "") if u.startswith("http")]
            sigla = filiacoes.get(pid, ("", ""))[1]
            saida.append({"nome": limpar_nome(p.get("nome_parlamentar") or ""), "partido": norm_partido(sigla) or sigla,
                          "emails": [p["email"].strip().lower()] if p.get("email") else [], "telefones": tels,
                          "endereco": f"Gabinete {gab}" if gab and len(gab) < 40 else "",
                          "pagina": site or f"https://{host}/parlamentar/{pid}", "foto": foto, "redes": redes_p})
        return saida
    return fn


def df():
    """CLDF: os cartões da legislatura atual trazem link, nome e partido; o resto vem do perfil."""
    lista = "https://www.cl.df.gov.br/deputados-2023-2026"
    pag = baixar(lista)
    pag = pag[pag.find("deputados-interno"):] if "deputados-interno" in pag else pag
    achados = {}
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([\s\S]{0,900}?)card-title">([^<]+)<[\s\S]{0,200}?card-text">([^<]*)<', pag):
        img = re.search(r'<img[^>]+src="([^"]+)"', m.group(2))
        achados[absoluto(lista, m.group(1))] = (limpar_nome(m.group(3)), partido_em(limpo(m.group(4)))[0],
                                                 absoluto(lista, html.unescape(img.group(1))) if img else "")
    if not achados:
        raise Falha("nenhum cartão de deputado na página da CLDF")
    ext = generico("DF")

    def extrair(u, p):
        nome, partido, foto = achados[u]
        d = ext(u, p, nome, partido)
        if foto:
            d["foto"] = foto
        return d
    return perfis("DF", list(achados), extrair)


def pa():
    """Alepa: os cartões não têm link; a chave de cada perfil está no JavaScript da página, na mesma ordem."""
    lista = "https://www.alepa.pa.gov.br/Home/Page/Deputados"
    pag = baixar(lista)
    m = re.search(r"'keys':\[([^\]]*)\]", pag)
    chaves = re.findall(r"'([^']+)'", m.group(1)) if m else []
    cartoes = re.findall(r"<img class='deputado-image' src='([^']*)'[\s\S]{0,200}?<div class='card-info'><span>[^<]*</span>"
                         r"<span>([^<]+)</span><p>([^<]*)</p>", pag)
    if not chaves or len(chaves) != len(cartoes):
        raise Falha(f"cartões ({len(cartoes)}) e perfis ({len(chaves)}) não batem na página da Alepa")
    achados = {}
    for k, (foto, nome, sigla) in zip(chaves, cartoes):
        achados[f"https://www.alepa.pa.gov.br/Institucional/Deputado/{k}"] = (
            limpar_nome(nome), norm_partido(sigla) or sigla.strip(), foto.replace("\\", "/").replace(" ", "%20"))
    ext = generico("PA")

    def extrair(u, p):
        nome, partido, foto = achados[u]
        d = ext(u, p, nome, partido)
        d["nome"], d["partido"], d["foto"] = nome, partido, foto
        return d
    return perfis("PA", list(achados), extrair)


def ms():
    """ALEMS: a lista de ramais (/Contacts/Search) tem a seção PARLAMENTARES com telefone e e-mail de cada gabinete.
    Guardamos só o gabinete; o nome do chefe de gabinete que aparece lá não é usado."""
    txt = texto(baixar("https://al.ms.gov.br/Contacts/Search"))
    i = txt.find("\nPARLAMENTARES\n")
    if i < 0:
        raise Falha("seção PARLAMENTARES não encontrada na lista de ramais da ALEMS")
    linhas = txt[i:].split("\n")[2:]
    saida, atual = [], None
    for j, l in enumerate(linhas):
        if l.isupper() and len(l) > 6 and not re.search(r"\d", l):
            break  # começou outra seção do órgão
        if j + 1 < len(linhas) and linhas[j + 1].startswith("Chefe de Gabinete"):
            atual = {"nome": l.strip(), "partido": "", "emails": [], "telefones": [], "endereco": "",
                     "pagina": "https://al.ms.gov.br/", "foto": "", "redes": []}
            saida.append(atual)
            continue
        if not atual:
            continue
        if re.match(r"(\(?\d{2}\)?\s*)?\d{4}-\d{4}", l):
            atual["telefones"] += telefones(l.split("Ramais")[0].split("Ramal")[0], "MS")
        if l.lower().startswith("email"):
            atual["emails"] += emails(l)
    return saida


def rs():
    dados = json.loads(baixar("https://ww4.al.rs.gov.br:5000/listarDestaqueDeputados",
                              cabecalhos={"Content-Type": "application/json"}))
    saida = []
    for d in dados.get("lista") or []:
        if d.get("codStatus") not in (1, "1", None):
            continue
        dig = re.sub(r"\D", "", d.get("telefoneDeputado") or "")
        tel = [f"({dig[:2]}) {dig[2:-4]}-{dig[-4:]}"] if len(dig) in (10, 11) else []
        saida.append({"nome": (d.get("nomeDeputado") or "").strip(),
                      "partido": norm_partido(d.get("siglaPartido")) or (d.get("siglaPartido") or "").strip(),
                      "emails": [d["emailDeputado"].strip()] if d.get("emailDeputado") else [], "telefones": tel,
                      "endereco": "", "pagina": f"https://ww4.al.rs.gov.br/deputados/{d.get('idDeputado')}",
                      "foto": d.get("fotoGrandeDeputado") or "", "redes": []})
    return saida

ESTADOS = {
    "SP": ("Assembleia Legislativa de São Paulo (Alesp)", sp),
    "MG": ("Assembleia Legislativa de Minas Gerais (ALMG)", mg),
    "BA": ("Assembleia Legislativa da Bahia (Alba)", ba),
    "RS": ("Assembleia Legislativa do Rio Grande do Sul (ALRS)", rs),
    "DF": ("Câmara Legislativa do Distrito Federal (CLDF)", df),
    "PA": ("Assembleia Legislativa do Pará (Alepa)", pa),
    "MS": ("Assembleia Legislativa de Mato Grosso do Sul (ALEMS)", ms),
}
SAPL = {
    "AC": ("Assembleia Legislativa do Acre (Aleac)", "sapl.al.ac.leg.br"),
    "AL": ("Assembleia Legislativa de Alagoas (ALE-AL)", "sapl.al.al.leg.br"),
    "PI": ("Assembleia Legislativa do Piauí (Alepi)", "sapl.al.pi.leg.br"),
    "PB": ("Assembleia Legislativa da Paraíba (ALPB)", "sapl3.al.pb.leg.br"),
    "RR": ("Assembleia Legislativa de Roraima (ALE-RR)", "sapl.al.rr.leg.br"),
    "TO": ("Assembleia Legislativa do Tocantins (Aleto)", "sapl.al.to.leg.br"),
}
for _uf, (_casa, _host) in SAPL.items():
    ESTADOS[_uf] = (_casa, sapl(_host, _uf))
for _uf, _cfg in GENERICOS.items():
    ESTADOS[_uf] = (_cfg["casa"], por_perfis(_uf, _cfg))


def coletar(ufs=None):
    """Devolve (lista de parlamentares, relatório por estado)."""
    todos, relatorio = [], {}
    for uf in sorted(ufs or ESTADOS):
        if uf not in ESTADOS:
            relatorio[uf] = {"ok": False, "erro": "estado ainda sem coletor"}
            continue
        nome_casa, fn = ESTADOS[uf]
        try:
            itens = depurar(uf, [d for d in fn() if d.get("nome")])
            vistos, lista = set(), []
            for d in itens:
                p = montar(uf, d, nome_casa)
                if p["id"] in vistos:
                    continue
                vistos.add(p["id"])
                lista.append(p)
            todos.extend(lista)
            relatorio[uf] = {"ok": True, "n": len(lista), "cadeiras": CADEIRAS[uf],
                             "com_email": sum(1 for p in lista if p["email"]),
                             "com_telefone": sum(1 for p in lista if p["telefones"])}
        except Exception as e:  # um estado fora do ar não derruba os outros
            relatorio[uf] = {"ok": False, "erro": str(e)[:200]}
        r = relatorio[uf]
        if r["ok"]:
            aviso = "" if abs(r["n"] - r["cadeiras"]) <= 3 else f"  <- esperado ~{r['cadeiras']}"
            print(f"  {uf}: {r['n']} deputados ({r['com_email']} com e-mail, {r['com_telefone']} com telefone){aviso}", flush=True)
        else:
            print(f"  {uf}: FALHOU — {r['erro']}", flush=True)
    return todos, relatorio


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ufs = [a.upper() for a in sys.argv[1:]] or None
    lista, rel = coletar(ufs)
    if ufs:
        for p in lista:
            print(json.dumps(p, ensure_ascii=False))
