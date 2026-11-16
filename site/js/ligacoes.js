/* Tempo Continuum — ligações entre matérias, dossiês, meta-dossiês e casos.
   Uma ligação é uma tag com o título do outro item (como a tag "Jones Manoel" liga a matéria à ficha dele):
   - a matéria com a tag "Morte de Renée Good" está ligada ao caso Morte de Renée Good;
   - o caso com a tag "ICE: A nova Gestapo" está ligado a esse dossiê; e assim por diante.
   A ligação vale nos dois sentidos: as duas páginas mostram uma à outra, não importa em qual delas a tag está.
   Dossiê e meta-dossiê também ficam ligados quando o dossiê está na lista "dossies" do meta-dossiê.
   Hierarquia (do menor para o maior): matéria < caso < dossiê < meta-dossiê. Cada página mostra uma caixa só para
   os itens maiores ligados a ela; os menores aparecem nas "Fontes no Tempo Continuum".
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

  // Hierarquia, do menor para o maior: matéria < caso < dossiê < meta-dossiê
  var NIVEL = { noticias: 0, casos: 1, dossies: 2, metadossies: 3 };
  var MESES = ['jan.', 'fev.', 'mar.', 'abr.', 'maio', 'jun.', 'jul.', 'ago.', 'set.', 'out.', 'nov.', 'dez.'];
  function data(iso) { var p = String(iso || '').slice(0, 10).split('-'); return p.length === 3 ? Number(p[2]) + ' ' + MESES[Number(p[1]) - 1] + ' ' + p[0] : ''; }
  function rotulo(l) {
    var x = l.item || {};
    if (l.tipo === 'noticias') return ['Matéria', data(x.data), x.editoria].filter(Boolean).join(' · ');
    if (l.tipo === 'casos') return 'Caso acompanhado' + (x.status ? ' · ' + String(x.status).toLowerCase() : '');
    var n = l.tipo === 'dossies' ? (x.capitulos || []).length : idsDossies(x).length;
    return l.tipo === 'dossies' ? 'Dossiê · ' + n + (n === 1 ? ' capítulo' : ' capítulos') : 'Meta-dossiê · ' + n + (n === 1 ? ' dossiê' : ' dossiês');
  }
  // Onde a ligação aparece na página do item atual:
  // 'caixa' (o outro é maior), 'fonte' (o outro é menor), 'relacionado' (mesmo nível) ou '' (dossiê que já é parte do meta-dossiê)
  function lugar(tipoAtual, l) {
    var a = NIVEL[tipoAtual], b = NIVEL[l.tipo];
    if (b > a) return 'caixa';
    if (b < a) return tipoAtual === 'metadossies' && l.como === 'lista' ? '' : 'fonte';
    return 'relacionado';
  }
  // Para as páginas: caixas só para os maiores; os menores entram como fontes; os do mesmo nível, como relacionados
  function paraPagina(lista, tipoAtual) {
    var caixas = [], fontes = [], relacionados = [];
    lista.forEach(function (l) {
      var onde = lugar(tipoAtual, l), x = l.item || {};
      if (onde === 'caixa') {
        caixas.push({ titulo: l.titulo, href: l.href, rotulo: rotulo(l),
          acao: l.tipo === 'casos' ? 'Ver o caso →' : l.tipo === 'dossies' ? 'Ler o dossiê →' : 'Ver o meta-dossiê →' });
      } else if (onde) {
        (onde === 'fonte' ? fontes : relacionados).push({ titulo: l.titulo, href: l.href, detalhe: rotulo(l), nivel: NIVEL[l.tipo], data: x.data || '' });
      }
    });
    // Fontes: as maiores primeiro; entre matérias, as mais recentes primeiro
    var ordem = function (p, q) { return q.nivel - p.nivel || String(q.data).localeCompare(String(p.data)); };
    fontes.sort(ordem); relacionados.sort(ordem);
    var nomes = { noticias: 'Matérias relacionadas', casos: 'Casos relacionados', dossies: 'Dossiês relacionados', metadossies: 'Meta-dossiês relacionados' };
    return { ligacoes: caixas, temLigacoes: caixas.length > 0, fontes: fontes, temFontes: fontes.length > 0,
      relacionados: relacionados, temRelacionados: relacionados.length > 0, tituloRelacionados: nomes[tipoAtual] || 'Relacionados' };
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

  window.TCLigacoes = { TIPOS: TIPOS, ORDEM: ORDEM, NIVEL: NIVEL, lugar: lugar, chave: chave, partes: partes, calcular: calcular, paraPagina: paraPagina, carregarIndices: carregarIndices };
})();
