"""Baixa os contatos oficiais dos deputados federais, senadores e deputados estaduais/distritais em exercício.

Fontes (oficiais, sem cadastro):
- Câmara dos Deputados: https://dadosabertos.camara.leg.br/api/v2/deputados  (lista + detalhe de cada um)
- Senado Federal:       https://legis.senado.leg.br/dadosabertos/senador/lista/atual  (lista + detalhe de cada um)
- Assembleias Legislativas e CLDF: os sites oficiais de cada uma (veja scripts/estaduais.py)

Grava dados/parlamentares.json, que a página contatos.html lê. Só guarda dados de contato do mandato
(gabinete, telefone, e-mail, página oficial e redes sociais); nada de CPF ou dados pessoais.
Se a Câmara ou o Senado falharem, nada é gravado. Se uma Assembleia falhar, os dados anteriores dela são mantidos.

Uso:  python scripts/parlamentares.py              (tudo)
      python scripts/parlamentares.py --estaduais  (só as Assembleias; mantém Câmara e Senado como estão)
"""
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "parlamentares.json"
AGENTE = "Mozilla/5.0 (compatible; TempoContinuum/1.0; contatos do Congresso)"
CAMARA = "https://dadosabertos.camara.leg.br/api/v2"
SENADO = "https://legis.senado.leg.br/dadosabertos"


def baixar(url, tentativas=4):
    pedido = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": AGENTE})
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(pedido, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == tentativas - 1:
                raise
            time.sleep(1.5 * (i + 1))


def lista(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def tel_df(numero):
    """'3215-5414' ou '33036333' -> '(61) 3215-5414'. Os gabinetes ficam todos em Brasília."""
    d = re.sub(r"\D", "", str(numero or ""))
    if len(d) == 10 and d.startswith("61"):
        d = d[2:]
    if len(d) == 8:
        return f"(61) {d[:4]}-{d[4:]}"
    return str(numero or "").strip()


def deputados():
    base = baixar(f"{CAMARA}/deputados?itens=1000&ordem=ASC&ordenarPor=nome")["dados"]

    def um(d):
        det = baixar(f"{CAMARA}/deputados/{d['id']}")["dados"]
        st = det.get("ultimoStatus") or {}
        gab = st.get("gabinete") or {}
        partes = []
        if gab.get("predio"):
            partes.append(f"Anexo {gab['predio']}" if str(gab["predio"]).isdigit() else str(gab["predio"]))
        if gab.get("andar"):
            partes.append(f"{gab['andar']}º andar")
        if gab.get("sala"):
            partes.append(f"Gabinete {gab['sala']}")
        endereco = ", ".join(partes)
        if endereco:
            endereco = "Câmara dos Deputados, " + endereco + " — Brasília/DF"
        redes = [r.strip() for r in lista(det.get("redeSocial")) if r and r.strip()]
        if det.get("urlWebsite"):
            redes.append(det["urlWebsite"].strip())
        return {
            "casa": "camara",
            "id": d["id"],
            "nome": st.get("nomeEleitoral") or d["nome"],
            "partido": st.get("siglaPartido") or d.get("siglaPartido") or "",
            "uf": st.get("siglaUf") or d.get("siglaUf") or "",
            "foto": d.get("urlFoto") or "",
            "email": gab.get("email") or d.get("email") or "",
            "telefones": [tel_df(gab["telefone"])] if gab.get("telefone") else [],
            "endereco": endereco,
            "pagina": f"https://www.camara.leg.br/deputados/{d['id']}",
            "redes": redes,
        }

    with ThreadPoolExecutor(max_workers=8) as ex:
        return list(ex.map(um, base))


def senadores():
    base = lista(baixar(f"{SENADO}/senador/lista/atual.json")["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"])

    def um(p):
        ip = p["IdentificacaoParlamentar"]
        cod = ip["CodigoParlamentar"]
        endereco = ""
        try:
            det = baixar(f"{SENADO}/senador/{cod}.json")["DetalheParlamentar"]["Parlamentar"]
            endereco = " ".join(((det.get("DadosBasicosParlamentar") or {}).get("EnderecoParlamentar") or "").split())
        except Exception:
            pass
        if endereco:
            endereco += " — Brasília/DF"
        tels = sorted(lista((ip.get("Telefones") or {}).get("Telefone")), key=lambda t: int(t.get("OrdemPublicacao") or 0))
        return {
            "casa": "senado",
            "id": int(cod),
            "nome": ip.get("NomeParlamentar") or "",
            "partido": ip.get("SiglaPartidoParlamentar") or "",
            "uf": ip.get("UfParlamentar") or "",
            "foto": (ip.get("UrlFotoParlamentar") or "").replace("http://", "https://"),
            "email": ip.get("EmailParlamentar") or "",
            "telefones": [tel_df(t["NumeroTelefone"]) for t in tels if t.get("IndicadorFax") != "Sim" and t.get("NumeroTelefone")],
            "endereco": endereco,
            "pagina": f"https://www25.senado.leg.br/web/senadores/senador/-/perfil/{cod}",
            "redes": [],
        }

    with ThreadPoolExecutor(max_workers=6) as ex:
        return list(ex.map(um, base))


def estaduais(anterior):
    """Coleta as Assembleias; para cada estado que falhar, reaproveita o que já estava no arquivo."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import estaduais as E
    print("Baixando deputados estaduais e distritais (Assembleias)…", flush=True)
    novos, rel = E.coletar()
    velhos = [p for p in anterior.get("parlamentares", []) if p.get("casa") == "estadual"]
    cobertura_velha = anterior.get("cobertura_estadual") or {}
    cobertura = {}
    for uf in sorted(E.CADEIRAS):
        r = rel.get(uf) or {"ok": False, "erro": "estado sem coletor"}
        if r["ok"]:
            cobertura[uf] = {"n": r["n"], "cadeiras": E.CADEIRAS[uf], "casa": E.ESTADOS[uf][0],
                             "atualizado_em": datetime.now().strftime("%Y-%m-%d"), "aviso": E.AVISOS.get(uf, "")}
        elif uf in cobertura_velha and any(p["uf"] == uf for p in velhos):
            novos += [p for p in velhos if p["uf"] == uf]
            cobertura[uf] = dict(cobertura_velha[uf], aviso=(cobertura_velha[uf].get("aviso") or "")
                                 or "A última atualização falhou; estes são os dados da coleta anterior.")
            print(f"  {uf}: mantidos os dados anteriores ({cobertura_velha[uf].get('atualizado_em')})", flush=True)
        else:
            cobertura[uf] = {"n": 0, "cadeiras": E.CADEIRAS[uf], "casa": E.ESTADOS.get(uf, (E.NOMES_CASAS.get(uf, ""),))[0],
                             "atualizado_em": "", "aviso": "Ainda não conseguimos coletar os contatos desta Assembleia."}
    return novos, cobertura


def main():
    so_estaduais = "--estaduais" in sys.argv
    anterior = {}
    if SAIDA.exists():
        try:
            anterior = json.loads(SAIDA.read_text(encoding="utf-8"))
        except ValueError:
            anterior = {}
    if so_estaduais:
        nacionais = [p for p in anterior.get("parlamentares", []) if p.get("casa") in ("camara", "senado")]
        if not nacionais:
            sys.exit("Ainda não há dados da Câmara e do Senado; rode sem --estaduais.")
    else:
        print("Baixando deputados federais (Câmara)…", flush=True)
        dep = deputados()
        print(f"  {len(dep)} deputados", flush=True)
        print("Baixando senadores (Senado)…", flush=True)
        sen = senadores()
        print(f"  {len(sen)} senadores", flush=True)
        if len(dep) < 400 or len(sen) < 70:
            sys.exit("Poucos parlamentares na resposta; o arquivo não foi alterado.")
        nacionais = dep + sen
    est, cobertura = estaduais(anterior)
    todos = sorted(nacionais + est, key=lambda p: p["nome"].lower())
    saida = {
        "atualizado_em": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "fontes": {
            "camara": "https://dadosabertos.camara.leg.br",
            "senado": "https://legis.senado.leg.br/dadosabertos",
            "estaduais": "sites oficiais das Assembleias Legislativas e da CLDF",
        },
        "cobertura_estadual": cobertura,
        "parlamentares": todos,
    }
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    n_est = sum(1 for p in todos if p["casa"] == "estadual")
    faltam = [uf for uf, c in cobertura.items() if not c["n"]]
    print(f"Gravado {SAIDA.relative_to(RAIZ)} ({len(todos)} parlamentares, {n_est} estaduais/distritais)."
          + (f" Sem dados: {', '.join(faltam)}." if faltam else ""))


if __name__ == "__main__":
    main()
