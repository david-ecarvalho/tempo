/* Tempo Continuum — tags e subtags.
   Uma tag pode ter subtag separada por barra: "violência/contra indígenas".
   - O site mostra "violência › contra indígenas".
   - Filtrar pela tag-mãe ("violência") traz tudo dessa tag, com ou sem subtag.
   - Filtrar pela subtag traz só aquele recorte.
   Maiúsculas, acentos e espaços em volta da barra são ignorados na comparação. */
(function () {
  'use strict';

  function norm(s) {
    return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
      .replace(/\s*\/\s*/g, '/').replace(/\s+/g, ' ').trim();
  }

  // "Violência / Contra indígenas" → { mae: "Violência", sub: "Contra indígenas" }
  function partes(tag) {
    var t = String(tag || '').trim(), i = t.indexOf('/');
    if (i < 0) return { mae: t, sub: '' };
    return { mae: t.slice(0, i).trim(), sub: t.slice(i + 1).trim() };
  }

  // Grafia limpa da tag (sem espaços sobrando em volta da barra)
  function limpa(tag) {
    var p = partes(tag);
    return p.sub ? p.mae + '/' + p.sub : p.mae;
  }

  function rotulo(tag) {
    var p = partes(tag);
    return p.sub ? p.mae + ' › ' + p.sub : p.mae;
  }

  // A tag do item atende ao filtro? O filtro pode ser uma tag-mãe ou uma tag com subtag.
  function atende(tagDoItem, filtro) {
    var t = norm(tagDoItem), f = norm(filtro);
    if (!f) return true;
    return t === f || (f.indexOf('/') < 0 && t.indexOf(f + '/') === 0);
  }

  // O item (lista de tags) atende a todos os filtros escolhidos?
  function atendeTodos(tagsDoItem, filtros) {
    return (filtros || []).every(function (f) {
      return (tagsDoItem || []).some(function (t) { return atende(t, f); });
    });
  }

  // Lista para os botões de filtro: cada tag-mãe (contando as matérias com qualquer subtag dela),
  // seguida das suas subtags. Tags-mãe por quantidade; subtags por quantidade dentro de cada mãe.
  // Devolve [{ tag, rotulo, n, sub: bool }]
  function contar(itens) {
    var maes = {};
    itens.forEach(function (tags) {
      var vistasMae = {}, vistasSub = {};
      (tags || []).forEach(function (t) {
        var p = partes(t);
        if (!p.mae) return;
        var km = norm(p.mae);
        var m = maes[km] || (maes[km] = { tag: p.mae, n: 0, subs: {}, grafias: {} });
        m.grafias[p.mae] = (m.grafias[p.mae] || 0) + 1;
        if (!vistasMae[km]) { m.n++; vistasMae[km] = true; }
        if (p.sub) {
          var ks = norm(p.mae + '/' + p.sub);
          var s = m.subs[ks] || (m.subs[ks] = { tag: p.mae + '/' + p.sub, n: 0 });
          if (!vistasSub[ks]) { s.n++; vistasSub[ks] = true; }
        }
      });
    });
    var porN = function (a, b) { return b.n - a.n || a.tag.localeCompare(b.tag, 'pt'); };
    var lista = [];
    // Grafia mostrada para a tag-mãe: a mais usada (empate: a primeira que apareceu)
    Object.keys(maes).forEach(function (k) {
      var g = maes[k].grafias;
      maes[k].tag = Object.keys(g).reduce(function (a, b) { return g[b] > g[a] ? b : a; });
    });
    Object.keys(maes).map(function (k) { return maes[k]; }).sort(porN).forEach(function (m) {
      lista.push({ tag: m.tag, rotulo: m.tag, n: m.n, sub: false });
      Object.keys(m.subs).map(function (k) { return m.subs[k]; }).sort(porN).forEach(function (s) {
        lista.push({ tag: s.tag, rotulo: rotulo(s.tag), n: s.n, sub: true });
      });
    });
    return lista;
  }

  window.TCTags = { norm: norm, partes: partes, limpa: limpa, rotulo: rotulo, atende: atende, atendeTodos: atendeTodos, contar: contar };
})();
