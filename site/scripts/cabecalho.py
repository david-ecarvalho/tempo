"""Lê o cabeçalho (entre linhas "---") dos arquivos .md de matérias e fichas.

É o mesmo subconjunto de YAML que js/markdown.js lê e grava: valores simples ("texto entre aspas",
números, true/false), listas na mesma linha (["a", "b"]) e listas em bloco, de valores ou de pares
chave: valor.
"""
import json
import re

_CHAVE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s+(.*)|\s*)$")


def _escalar(v):
    v = v.strip()
    if v == "":
        return ""
    if v[0] == '"':
        try:
            return json.loads(v)
        except ValueError:
            return v[1:-1]
    if v[0] == "'":
        return v[1:v.rfind("'")].replace("''", "'")
    if v[0] == "[":
        try:
            return json.loads(v)
        except ValueError:
            dentro = v[1:v.rfind("]")].strip()
            return [_escalar(x) for x in dentro.split(",")] if dentro else []
    if v == "true":
        return True
    if v == "false":
        return False
    if v in ("null", "~"):
        return ""
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def _recuo(linha):
    return len(linha) - len(linha.lstrip(" "))


def _ler_cabecalho(texto):
    dados, linhas, i = {}, texto.split("\n"), 0
    while i < len(linhas):
        linha = linhas[i]
        if not linha.strip() or linha.lstrip().startswith("#"):
            i += 1
            continue
        m = _CHAVE.match(linha)
        if not m:
            i += 1
            continue
        chave, valor = m.group(1), m.group(2)
        if valor is not None and valor.strip():
            dados[chave] = _escalar(valor)
            i += 1
            continue
        lista = []
        i += 1
        while i < len(linhas) and (not linhas[i].strip() or _recuo(linhas[i]) > 0):
            l = linhas[i]
            mi = re.match(r"^(\s*)- ?(.*)$", l) if l.strip() else None
            if not mi:
                i += 1
                continue
            base, resto = len(mi.group(1)), mi.group(2)
            par = _CHAVE.match(resto)
            if par:
                item = {par.group(1): _escalar(par.group(2) or "")}
                i += 1
                while (i < len(linhas) and linhas[i].strip() and _recuo(linhas[i]) > base
                       and not linhas[i][base:].startswith("- ")):
                    p2 = _CHAVE.match(linhas[i].strip())
                    if p2:
                        item[p2.group(1)] = _escalar(p2.group(2) or "")
                    i += 1
                lista.append(item)
            else:
                lista.append(_escalar(resto))
                i += 1
        dados[chave] = lista
    return dados


def ler(texto):
    """Devolve (dados do cabeçalho, corpo)."""
    texto = texto.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    m = re.match(r"^---\n(.*?)\n---[ \t]*(?:\n|$)", texto, re.S)
    if not m:
        return {}, texto.strip()
    return _ler_cabecalho(m.group(1)), texto[m.end():].strip()
