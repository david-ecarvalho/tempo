"""Gera dados/mapa-ufs.json: o contorno de cada estado em caminhos SVG, para o mapa clicável de contatos.html.

Fonte: malha oficial do IBGE (API de malhas, qualidade mínima, divisão por UF):
https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF

Só precisa rodar de novo se quiser mudar o desenho do mapa; as fronteiras não mudam.
Uso:  python scripts/gerar-mapa.py
"""
import gzip
import json
import math
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "mapa-ufs.json"
FONTE = ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
         "?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF")
CODIGOS = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI",
           "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
           "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}
# Estados pequenos demais para a sigla caber dentro: o rótulo vai para o mar (ou para fora), com uma linha até o estado
FORA = {"RN": (70, -18), "PB": (78, 0), "PE": (78, 16), "AL": (66, 26), "SE": (56, 34), "ES": (58, 12), "RJ": (52, 34),
        "DF": (40, -26)}
LARGURA = 1000
LAT0 = math.radians(-15)


def dp(pontos, tol):
    """Douglas-Peucker: tira pontos que não mudam o desenho na escala do mapa."""
    if len(pontos) < 3:
        return pontos
    (x1, y1), (x2, y2) = pontos[0], pontos[-1]
    dx, dy = x2 - x1, y2 - y1
    norma = math.hypot(dx, dy) or 1e-9
    i_max, d_max = 0, -1.0
    for i in range(1, len(pontos) - 1):
        x, y = pontos[i]
        d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norma
        if d > d_max:
            i_max, d_max = i, d
    if d_max <= tol:
        return [pontos[0], pontos[-1]]
    return dp(pontos[:i_max + 1], tol)[:-1] + dp(pontos[i_max:], tol)


def area_centro(anel):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(anel, anel[1:] + anel[:1]):
        f = x1 * y2 - x2 * y1
        a += f
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    a /= 2
    if abs(a) < 1e-9:
        return 0.0, anel[0]
    return abs(a), (cx / (6 * a), cy / (6 * a))


def main():
    req = urllib.request.Request(FONTE, headers={"Accept": "application/json", "User-Agent": "TempoContinuum/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        bruto = r.read()
    if bruto[:2] == b"\x1f\x8b":  # o IBGE responde comprimido
        bruto = gzip.decompress(bruto)
    geo = json.loads(bruto.decode("utf-8"))

    def projetar(lon, lat):
        return math.radians(lon) * math.cos(LAT0), -math.radians(lat)

    estados = {}
    for f in geo["features"]:
        uf = CODIGOS[str(f["properties"]["codarea"])]
        g = f["geometry"]
        polis = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        estados[uf] = [[[projetar(*pt[:2]) for pt in anel] for anel in poli] for poli in polis]

    xs = [x for ps in estados.values() for poli in ps for anel in poli for x, _ in anel]
    ys = [y for ps in estados.values() for poli in ps for anel in poli for _, y in anel]
    margem_dir = 0.09 * (max(xs) - min(xs))  # espaço no mar para os rótulos de fora
    esc = LARGURA / (max(xs) - min(xs) + margem_dir)
    altura = (max(ys) - min(ys)) * esc
    x0, y0 = min(xs), min(ys)

    saida = {}
    for uf, polis in sorted(estados.items()):
        partes, maior = [], (0.0, (0, 0))
        for poli in polis:
            for k, anel in enumerate(poli):
                pts = [((x - x0) * esc + 4, (y - y0) * esc + 4) for x, y in anel]
                if pts[0] == pts[-1]:
                    pts = pts[:-1]
                # anel fechado: simplifica as duas metades (o início e o fim do anel são o mesmo ponto)
                meio = len(pts) // 2
                simples = dp(pts[:meio + 1], 0.6)[:-1] + dp(pts[meio:] + [pts[0]], 0.6)[:-1]
                if len(simples) < 3:
                    continue
                if k == 0:
                    a, c = area_centro(simples)
                    if a > maior[0]:
                        maior = (a, c)
                partes.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in simples) + "Z")
        cx, cy = maior[1]
        item = {"d": "".join(partes), "x": round(cx, 1), "y": round(cy, 1)}
        if uf in FORA:
            dx, dy = FORA[uf]
            item["rx"], item["ry"] = round(cx + dx, 1), round(cy + dy, 1)
        saida[uf] = item

    dados = {"fonte": "IBGE — malha de UFs (qualidade mínima)", "largura": LARGURA + 8,
             "altura": round(altura + 8, 1), "ufs": saida}
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Gravado {SAIDA.relative_to(RAIZ)} ({SAIDA.stat().st_size // 1024} KB, {len(saida)} estados).")


if __name__ == "__main__":
    main()
