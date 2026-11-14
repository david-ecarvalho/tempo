"""Monta a versão publicável do site na pasta _site/.

    python scripts/publicar.py

O que faz:
- refaz os índices de dados/ (scripts/gerar-indice.py);
- copia para _site/ só o que o público usa: as páginas, js/, dados/, conteudo/, imagens/, logos/ e arquivos/;
- deixa de fora o editor (admin/, que só funciona com o servidor local), os scripts, o .github e os textos
  de documentação;
- deixa de fora os dossiês que ainda estão com o texto-modelo do editor ("Texto do capítulo..."), para
  não publicar dossiê vazio. Eles continuam no site local e entram sozinhos quando o texto for escrito.

A pasta _site/ pode ir para qualquer hospedagem de site estático (GitHub Pages, Netlify, Cloudflare Pages,
um servidor comum). O GitHub Actions (.github/workflows/publicar-site.yml) usa este mesmo script.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "_site"

PASTAS = ["js", "dados", "conteudo", "imagens", "logos", "arquivos"]
IGNORAR = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "Thumbs.db", "desktop.ini")

# Trecho que o editor põe em todo dossiê novo (admin/editor.js); se ainda estiver lá, o dossiê não foi escrito.
MODELO_DOSSIE = 'Texto do capítulo. Use "### " para as subdivisões dentro dele.'


def dossies_incompletos():
    pasta = RAIZ / "conteudo" / "dossies"
    if not pasta.exists():
        return set()
    return {a.stem for a in pasta.glob("*.md") if MODELO_DOSSIE in a.read_text(encoding="utf-8")}


def main():
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "gerar-indice.py")], check=True)

    if SAIDA.exists():
        shutil.rmtree(SAIDA)
    SAIDA.mkdir()

    for pagina in sorted(RAIZ.glob("*.html")):
        shutil.copy2(pagina, SAIDA / pagina.name)
    for pasta in PASTAS:
        if (RAIZ / pasta).exists():
            shutil.copytree(RAIZ / pasta, SAIDA / pasta, ignore=IGNORAR)

    fora = dossies_incompletos()
    if fora:
        indice = SAIDA / "dados" / "dossies.json"
        dossies = [d for d in json.loads(indice.read_text(encoding="utf-8")) if d["id"] not in fora]
        indice.write_text(json.dumps(dossies, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        for id_ in fora:
            (SAIDA / "conteudo" / "dossies" / f"{id_}.md").unlink(missing_ok=True)
            (SAIDA / "arquivos" / "dossies" / f"{id_}.pdf").unlink(missing_ok=True)
        print(f"Ficaram de fora {len(fora)} dossiê(s) ainda com o texto-modelo: {', '.join(sorted(fora))}")

    # Sem isto, o GitHub Pages passaria o site pelo Jekyll quando publicado a partir de um branch.
    (SAIDA / ".nojekyll").write_text("", encoding="utf-8")
    (SAIDA / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")

    arquivos = [a for a in SAIDA.rglob("*") if a.is_file()]
    tamanho = sum(a.stat().st_size for a in arquivos) / 1024 / 1024
    print(f"Site pronto em {SAIDA.relative_to(RAIZ)}/: {len(arquivos)} arquivos, {tamanho:.1f} MB")


if __name__ == "__main__":
    main()
