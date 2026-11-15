/* Tempo Continuum — ligações entre matérias, dossiês, meta-dossiês e casos.
   Uma ligação é uma tag com o título do outro item (como a tag "Jones Manoel" liga a matéria à ficha dele):
   - a matéria com a tag "Morte de Renée Good" está ligada ao caso Morte de Renée Good;
   - o caso com a tag "ICE: A nova Gestapo" está ligado a esse dossiê; e assim por diante.
   A ligação vale nos dois sentidos: as duas páginas mostram uma à outra, não importa em qual delas a tag está.
   Dossiê e meta-dossiê também ficam ligados quando o dossiê está na lista "dossies" do meta-dossiê.
   Usado pelas páginas (materia.html, dossie.html, caso.html) e pelo editor (admin/editor.js). */
(function () {
  'use strict';

  var TIPOS = {
    noticias: { nome: 'matéria', artigo: 'a', pagina: function (id) { return 'materia.html?id=' + encodeURIComponent(id); } },
    dossies: { nome: 'dossiê', artigo: 'o', pagina: function (id) { return 'dossie.html?id=' + encodeURIComponent(id); } },
    metadossies: { nome: 'meta-dossiê', artigo: 'o', pagina: function (id) { return 'dossie.html?meta=' + encodeURIComponent(id); } },
    casos: { nome: 'caso', artigo: 'o', pagina: function (id) { return 'caso.html?id=' + encodeURIComponent(id); } }
  };
  var ORDEM = ['casos', 'dossies', 'metadossies', 'noticias'];

  function chave(s) {
    return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
      .replace(/\s*\/\s*/g, '/').replace(/\s+/g, ' ').trim();
  }
  // Cada parte das tags ("ICE: A nova Gestapo" ou "violência/contra indígenas"), sem acento nem maiúscula
  function partes(tags) {
    var p = {};
    (tags || []).forEach(function (t) { String(t).split('/').forEach(function (x) { var k = chave(x); if (k) p[k] = true; }); });
    return p;
  }
  // Ids dos dossiês de um meta-dossiê: no índice vêm como [{ id, titulo }]; no arquivo, como ["id", ...]
  function idsDossies(x) { return (x && x.dossies || []).map(function (d) { return typeof d === 'string' ? d : d && d.id; }).filter(Boolean); }

  // atual: { tipo, id, titulo, tags, dossies (só meta-dossiê) }; indices: { noticias, dossies, metadossies, casos }
  // Devolve [{ tipo, id, titulo, href, nome, artigo, como }] — como: 'tag' (a tag está no item atual),
  // 'outro' (a tag está no outro item) ou 'lista' (dossiê na lista do meta-dossiê)
  function calcular(atual, indices) {
    var minhas = partes(atual.tags), meuTitulo = chave(atual.titulo), saida = [], visto = {};
    var meusDossies = atual.tipo === 'metadossies' ? idsDossies(atual) : [];
    ORDEM.forEach(function (tipo) {
      (indices[tipo] || []).forEach(function (x) {
        if (!x || !x.id || !x.titulo || (tipo === atual.tipo && x.id === atual.id)) return;
        // A lista do meta-dossiê vale primeiro: é ela que põe o dossiê dentro do meta-dossiê
        var como = '';
        if (atual.tipo === 'metadossies' && tipo === 'dossies' && meusDossies.indexOf(x.id) >= 0) como = 'lista';
        else if (atual.tipo === 'dossies' && tipo === 'metadossies' && idsDossies(x).indexOf(atual.id) >= 0) como = 'lista';
        else if (minhas[chave(x.titulo)]) como = 'tag';
        else if (meuTitulo && partes(x.tags)[meuTitulo]) como = 'outro';
        if (!como || visto[tipo + '/' + x.id]) return;
        visto[tipo + '/' + x.id] = true;
        saida.push({ tipo: tipo, id: x.id, titulo: x.titulo, href: TIPOS[tipo].pagina(x.id), nome: TIPOS[tipo].nome, artigo: TIPOS[tipo].artigo,
          como: como, item: x });
      });
    });
    return saida;
  }

  // Para as páginas: quadros (casos, dossiês, meta-dossiês) e a lista de matérias relacionadas
  var MESES = ['jan.', 'fev.', 'mar.', 'abr.', 'maio', 'jun.', 'jul.', 'ago.', 'set.', 'out.', 'nov.', 'dez.'];
  function data(iso) { var p = String(iso || '').slice(0, 10).split('-'); return p.length === 3 ? Number(p[2]) + ' ' + MESES[Number(p[1]) - 1] + ' ' + p[0] : ''; }
  function paraPagina(lista) {
    var quadros = [], materias = [];
    lista.forEach(function (l) {
      var x = l.item || {};
      if (l.tipo === 'noticias') {
        materias.push({ titulo: l.titulo, href: l.href, detalhe: [data(x.data), x.editoria].filter(Boolean).join(' · ') });
        return;
      }
      var n = l.tipo === 'dossies' ? (x.capitulos || []).length : l.tipo === 'metadossies' ? idsDossies(x).length : 0;
      quadros.push({
        titulo: l.titulo, href: l.href,
        rotulo: l.tipo === 'casos' ? 'Caso acompanhado' + (x.status ? ' · ' + String(x.status).toLowerCase() : '')
          : l.tipo === 'dossies' ? 'Dossiê · ' + n + (n === 1 ? ' capítulo' : ' capítulos')
          : 'Meta-dossiê · ' + n + (n === 1 ? ' dossiê' : ' dossiês'),
        acao: l.tipo === 'casos' ? 'Ver o caso →' : l.tipo === 'dossies' ? 'Ler o dossiê →' : 'Ver o meta-dossiê →'
      });
    });
    return { ligacoes: quadros, temLigacoes: quadros.length > 0, materiasLigadas: materias, temMateriasLigadas: materias.length > 0 };
  }
  // Os quatro índices que as ligações usam
  function carregarIndices(base, aoCarregar) {
    var indices = {};
    ORDEM.forEach(function (tipo) {
      fetch((base || '') + 'dados/' + tipo + '.json', { cache: 'no-cache' })
        .then(function (r) { return r.ok ? r.json() : []; })
        .catch(function () { return []; })
        .then(function (lista) { indices[tipo] = Array.isArray(lista) ? lista : []; aoCarregar(indices); });
    });
  }

  window.TCLigacoes = { TIPOS: TIPOS, ORDEM: ORDEM, chave: chave, partes: partes, calcular: calcular, paraPagina: paraPagina, carregarIndices: carregarIndices };
})();
