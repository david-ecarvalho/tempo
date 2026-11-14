/* Tempo Continuum — matérias e fichas em Markdown.
   Cada arquivo .md tem um cabeçalho entre linhas "---" (formato YAML simples) e o texto embaixo.

   Matéria (conteudo/noticias/<id>.md):
     ---
     titulo: "..."
     data: "2026-11-05T22:24:00"
     editado: "2026-11-06T09:10:00"     (opcional: última edição, mostrada como "Atualizada em …")
     tags: ["trabalho", "violência/contra indígenas"]
     ...
     ---
     Texto da matéria em Markdown (## intertítulos, **negrito**, [links](https://...), > citações, listas, ![imagem](...)).

   Ficha (conteudo/politicos/<id>.md): no cabeçalho, os dados de identificação, os selos, a caixa de dados e as
   eleições; no texto, uma seção "## " para cada parte:
     ## Resumo                       parágrafo
     ## Trajetória                   - **2018:** o que aconteceu
     ## Atuação parlamentar          - item      (o título desta seção é livre)
     ## Posições declaradas          - item
     ## Controvérsias e processos    - item
     ## Fontes                       - [Título — Veículo, data](https://...)

   Votação (conteudo/votacoes/<id>.md): no cabeçalho, os dados da consulta do e-Cidadania (sigla, ementa,
   ecidadania_id, votos_sim, votos_nao…) e a recomendacao ("sim" ou "nao"); no texto, a nossa descrição.

   Dossiê (conteudo/dossies/<id>.md): cabeçalho parecido com o da matéria (titulo, linha, data, autor, capa, tags…);
   no texto, cada "## Título" abre um capítulo.

   Usado pelas páginas (materia.html, ficha.html, dossie.html) e pelo editor (admin/). */
(function () {
  'use strict';

  // =========================================================================
  // Cabeçalho (subconjunto de YAML)
  // =========================================================================
  function valorEscalar(v) {
    v = v.trim();
    if (v === '') return '';
    if (v[0] === '"') { try { return JSON.parse(v); } catch (e) { return v.slice(1, -1); } }
    if (v[0] === "'") return v.slice(1, v.lastIndexOf("'")).replace(/''/g, "'");
    if (v[0] === '[') {
      try { return JSON.parse(v); } catch (e) {}
      var dentro = v.slice(1, v.lastIndexOf(']')).trim();
      return dentro ? dentro.split(',').map(valorEscalar) : [];
    }
    if (v === 'true') return true;
    if (v === 'false') return false;
    if (v === 'null' || v === '~') return '';
    if (/^-?\d+$/.test(v)) return Number(v);
    return v;
  }

  function separarChave(linha) {
    var m = /^([A-Za-z_][A-Za-z0-9_]*):(?:\s+(.*)|\s*)$/.exec(linha);
    return m ? { chave: m[1], valor: m[2] === undefined ? null : m[2] } : null;
  }

  function lerCabecalho(texto) {
    var dados = {}, linhas = texto.split('\n'), i = 0;
    var recuo = function (l) { return l.length - l.replace(/^ +/, '').length; };
    while (i < linhas.length) {
      var linha = linhas[i];
      if (!linha.trim() || /^\s*#/.test(linha)) { i++; continue; }
      var kv = separarChave(linha);
      if (!kv) { i++; continue; }
      if (kv.valor !== null && kv.valor.trim() !== '') { dados[kv.chave] = valorEscalar(kv.valor); i++; continue; }
      // Lista em bloco
      var lista = [];
      i++;
      while (i < linhas.length && (linhas[i].trim() === '' || recuo(linhas[i]) > 0)) {
        var l = linhas[i];
        if (!l.trim()) { i++; continue; }
        var m = /^(\s*)- ?(.*)$/.exec(l);
        if (!m) { i++; continue; }
        var base = m[1].length, resto = m[2], par = separarChave(resto);
        if (par) {
          var item = {};
          item[par.chave] = par.valor === null ? '' : valorEscalar(par.valor);
          i++;
          while (i < linhas.length && linhas[i].trim() !== '' && recuo(linhas[i]) > base && !/^\s*- /.test(linhas[i].slice(base))) {
            var p2 = separarChave(linhas[i].trim());
            if (p2) item[p2.chave] = p2.valor === null ? '' : valorEscalar(p2.valor);
            i++;
          }
          lista.push(item);
        } else {
          lista.push(valorEscalar(resto));
          i++;
        }
      }
      dados[kv.chave] = lista;
    }
    return dados;
  }

  function escalarYaml(v) {
    if (typeof v === 'boolean') return v ? 'true' : 'false';
    if (typeof v === 'number' && isFinite(v)) return String(v);
    return JSON.stringify(v == null ? '' : String(v));
  }

  function escreverCabecalho(dados, ordem) {
    var chaves = (ordem || []).filter(function (k) { return k in dados; });
    Object.keys(dados).forEach(function (k) { if (chaves.indexOf(k) < 0) chaves.push(k); });
    var saida = [];
    chaves.forEach(function (k) {
      var v = dados[k];
      if (v === undefined) return;
      if (!Array.isArray(v)) { saida.push(k + ': ' + escalarYaml(v)); return; }
      if (!v.length) { saida.push(k + ': []'); return; }
      if (v.every(function (x) { return typeof x !== 'object' || x === null; })) {
        saida.push(k + ': [' + v.map(escalarYaml).join(', ') + ']');
        return;
      }
      saida.push(k + ':');
      v.forEach(function (item) {
        Object.keys(item).forEach(function (c, j) {
          saida.push((j === 0 ? '  - ' : '    ') + c + ': ' + escalarYaml(item[c]));
        });
      });
    });
    return saida.join('\n');
  }

  // Separa o arquivo em { dados (cabeçalho), corpo (texto) }
  function ler(texto) {
    texto = String(texto || '').replace(/^﻿/, '').replace(/\r\n?/g, '\n');
    var m = /^---\n([\s\S]*?)\n---[ \t]*(?:\n|$)/.exec(texto);
    if (!m) return { dados: {}, corpo: texto.trim() };
    return { dados: lerCabecalho(m[1]), corpo: texto.slice(m[0].length).replace(/^\n+/, '').replace(/\s+$/, '') };
  }

  function escrever(dados, corpo, ordem) {
    return '---\n' + escreverCabecalho(dados, ordem) + '\n---\n\n' + String(corpo || '').replace(/\r\n?/g, '\n').trim() + '\n';
  }

  // =========================================================================
  // Texto em Markdown → blocos (usados pela página da matéria e pela prévia do editor)
  // =========================================================================
  function caminhoImagem(src) {
    return /^https?:/i.test(src) ? src : String(src || '').replace(/^\/+/, '').replace(/^tempocontinuum\//, '');
  }

  function inline(texto) {
    var segs = [], re = /\*\*([^*]+)\*\*|__([^_]+)__|\*([^*]+)\*|_([^_]+)_|\[([^\]]+)\]\(([^)\s]+)\)/g, ultimo = 0, m;
    var seguro = function (h) { return /^(https?:|mailto:|#|[a-z0-9._\/?=&-]+$)/i.test(h) ? h : '#'; };
    var simples = function (t) { if (t) segs.push({ t: t, simples: true, link: false, forte: false, enfase: false }); };
    texto = String(texto || '');
    while ((m = re.exec(texto))) {
      simples(texto.slice(ultimo, m.index));
      if (m[1] || m[2]) segs.push({ t: m[1] || m[2], forte: true, link: false, enfase: false, simples: false });
      else if (m[3] || m[4]) segs.push({ t: m[3] || m[4], enfase: true, link: false, forte: false, simples: false });
      else { var h = seguro(m[6]); segs.push({ t: m[5], href: h, alvo: /^https?:/i.test(h) ? '_blank' : '_self', link: true, forte: false, enfase: false, simples: false }); }
      ultimo = re.lastIndex;
    }
    simples(texto.slice(ultimo));
    return segs;
  }

  function blocos(md) {
    var saida = [], par = [], cit = [], lista = null;
    var vazio = { h2: false, h3: false, p: false, quote: false, ul: false, ol: false, img: false };
    var bloco = function (tipo, extra) { var b = Object.assign({}, vazio, extra || {}); b[tipo] = true; saida.push(b); };
    var fechar = function () {
      if (par.length) { bloco('p', { segs: inline(par.join(' ')) }); par = []; }
      if (cit.length) { bloco('quote', { segs: inline(cit.join(' ')) }); cit = []; }
      if (lista) { bloco(lista.tipo, { itens: lista.itens }); lista = null; }
    };
    String(md || '').replace(/\r/g, '').split('\n').forEach(function (linha) {
      var l = linha.trim(), m;
      if (!l) { fechar(); return; }
      if ((m = l.match(/^###\s+(.*)/))) { fechar(); bloco('h3', { segs: inline(m[1]) }); return; }
      if ((m = l.match(/^##?\s+(.*)/))) { fechar(); bloco('h2', { segs: inline(m[1]) }); return; }
      if ((m = l.match(/^!\[([^\]]*)\]\(([^)\s]+)\)$/))) { fechar(); bloco('img', { alt: m[1], temAlt: !!m[1], src: caminhoImagem(m[2]) }); return; }
      if ((m = l.match(/^>\s?(.*)/))) { if (par.length || lista) fechar(); cit.push(m[1]); return; }
      if ((m = l.match(/^[-*+]\s+(.*)/))) { if (par.length || cit.length || (lista && lista.tipo !== 'ul')) fechar(); lista = lista || { tipo: 'ul', itens: [] }; lista.itens.push({ segs: inline(m[1]) }); return; }
      if ((m = l.match(/^\d+[.)]\s+(.*)/))) { if (par.length || cit.length || (lista && lista.tipo !== 'ol')) fechar(); lista = lista || { tipo: 'ol', itens: [] }; lista.itens.push({ segs: inline(m[1]) }); return; }
      if (cit.length || lista) fechar();
      par.push(l);
    });
    fechar();
    return saida;
  }

  // HTML seguro a partir do Markdown (prévia do editor)
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; });
  }
  function segsHtml(segs) {
    return segs.map(function (s) {
      if (s.forte) return '<strong>' + esc(s.t) + '</strong>';
      if (s.enfase) return '<em>' + esc(s.t) + '</em>';
      if (s.link) return '<a href="' + esc(s.href) + '" target="_blank" rel="noopener noreferrer">' + esc(s.t) + '</a>';
      return esc(s.t);
    }).join('');
  }
  function html(md, base) {
    return blocos(md).map(function (b) {
      if (b.h2) return '<h2>' + segsHtml(b.segs) + '</h2>';
      if (b.h3) return '<h3>' + segsHtml(b.segs) + '</h3>';
      if (b.p) return '<p>' + segsHtml(b.segs) + '</p>';
      if (b.quote) return '<blockquote>' + segsHtml(b.segs) + '</blockquote>';
      if (b.img) return '<figure><img src="' + esc(/^https?:/i.test(b.src) ? b.src : (base || '') + b.src) + '" alt="' + esc(b.alt) + '" referrerpolicy="no-referrer">' + (b.alt ? '<figcaption>' + esc(b.alt) + '</figcaption>' : '') + '</figure>';
      var tag = b.ul ? 'ul' : 'ol';
      return '<' + tag + '>' + b.itens.map(function (i) { return '<li>' + segsHtml(i.segs) + '</li>'; }).join('') + '</' + tag + '>';
    }).join('\n');
  }

  // =========================================================================
  // Matérias
  // =========================================================================
  // "editado" (opcional): data e hora da última edição, mostrada na matéria como "Atualizada em …"
  var ORDEM_MATERIA = ['titulo', 'linha', 'data', 'editado', 'editoria', 'tags', 'autor', 'foto', 'legenda', 'credito', 'destaque'];

  function lerMateria(texto) {
    var r = ler(texto), m = r.dados;
    m.tags = Array.isArray(m.tags) ? m.tags.map(String) : (m.tags ? [String(m.tags)] : []);
    m.destaque = m.destaque === true;
    m.corpo = r.corpo;
    return m;
  }

  function escreverMateria(m) {
    var dados = {};
    ORDEM_MATERIA.forEach(function (k) {
      if (k === 'tags') dados.tags = (m.tags || []).filter(Boolean);
      else if (k === 'destaque') dados.destaque = !!m.destaque;
      else if (k === 'editado') { if (m.editado) dados.editado = String(m.editado); }   // só grava se houver
      else dados[k] = m[k] == null ? '' : String(m[k]);
    });
    return escrever(dados, m.corpo || '', ORDEM_MATERIA);
  }

  // =========================================================================
  // Fichas de políticos
  // =========================================================================
  var ORDEM_FICHA = ['nome', 'iniciais', 'foto', 'categoria', 'cargo_curto', 'partido', 'uf', 'chamada', 'subtitulo',
    'atualizado', 'selos', 'dados', 'eleicoes', 'nota_eleicoes'];
  var SECOES = { resumo: 'Resumo', trajetoria: 'Trajetória', posicoes: 'Posições declaradas', controversias: 'Controvérsias e processos', fontes: 'Fontes' };

  function chave(s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim(); }

  // Itens de lista "- ..." de uma seção (linhas recuadas continuam o item anterior)
  function itensLista(linhas) {
    var itens = [];
    linhas.forEach(function (l) {
      var m = /^\s*[-*+]\s+(.*)$/.exec(l);
      if (m) itens.push(m[1].trim());
      else if (l.trim() && itens.length) itens[itens.length - 1] += ' ' + l.trim();
    });
    return itens;
  }

  function lerFicha(texto) {
    var r = ler(texto), f = r.dados;
    ['selos', 'dados', 'eleicoes'].forEach(function (k) { if (!Array.isArray(f[k])) f[k] = []; });
    f.selos.forEach(function (s) { s.destaque = s.destaque === true; });
    f.eleicoes.forEach(function (e) { e.destaque = e.destaque === true; });
    var secoes = {}, atual = null;
    r.corpo.split('\n').forEach(function (l) {
      var m = /^##\s+(.*)$/.exec(l.trim());
      if (m) {
        var t = m[1].trim(), k = chave(t), achou = null;
        Object.keys(SECOES).forEach(function (s) { if (chave(SECOES[s]) === k) achou = s; });
        if (!achou) { achou = 'atuacao'; f.atuacao_titulo = t; }
        atual = secoes[achou] = [];
        return;
      }
      if (atual) atual.push(l);
    });
    f.resumo = (secoes.resumo || []).join('\n').trim().split(/\n\s*\n/).map(function (p) { return p.replace(/\s*\n\s*/g, ' ').trim(); }).filter(Boolean).join(' ');
    f.trajetoria = itensLista(secoes.trajetoria || []).map(function (t) {
      var m = /^\*\*(.+?):\*\*\s*(.*)$/.exec(t) || /^\*\*(.+?)\*\*:?\s*(.*)$/.exec(t);
      return m ? { quando: m[1].trim(), fato: m[2].trim() } : { quando: '', fato: t };
    });
    f.atuacao = itensLista(secoes.atuacao || []);
    if (!f.atuacao_titulo) f.atuacao_titulo = 'Atuação parlamentar';
    f.posicoes = itensLista(secoes.posicoes || []);
    f.controversias = itensLista(secoes.controversias || []);
    f.fontes = itensLista(secoes.fontes || []).map(function (t) {
      var m = /^\[(.*)\]\((\S+?)\)\s*$/.exec(t);
      return m ? { titulo: m[1].trim(), url: m[2] } : { titulo: t, url: /^https?:\/\/\S+$/.test(t) ? t : '' };
    });
    return f;
  }

  // Texto (corpo) da ficha a partir das partes
  function corpoFicha(f) {
    var partes = [];
    var secao = function (titulo, conteudo) { if (conteudo) partes.push('## ' + titulo + '\n\n' + conteudo); };
    var lista = function (v) { return (v || []).filter(Boolean).map(function (i) { return '- ' + i; }).join('\n'); };
    secao(SECOES.resumo, String(f.resumo || '').trim());
    secao(SECOES.trajetoria, (f.trajetoria || []).filter(function (t) { return t && (t.quando || t.fato); }).map(function (t) {
      return '- ' + (t.quando ? '**' + t.quando + ':** ' : '') + (t.fato || '');
    }).join('\n'));
    secao(f.atuacao_titulo || 'Atuação parlamentar', lista(f.atuacao));
    secao(SECOES.posicoes, lista(f.posicoes));
    secao(SECOES.controversias, lista(f.controversias));
    secao(SECOES.fontes, (f.fontes || []).filter(function (fo) { return fo && (fo.titulo || fo.url); }).map(function (fo) {
      return '- ' + (fo.url ? '[' + (fo.titulo || fo.url) + '](' + fo.url + ')' : fo.titulo);
    }).join('\n'));
    return partes.join('\n\n');
  }

  // Modelo de texto para uma ficha nova
  var MODELO_FICHA = '## Resumo\n\nDe 3 a 5 frases, só com fatos verificáveis.\n\n## Trajetória\n\n- **2018:** O que aconteceu\n\n' +
    '## Atuação parlamentar\n\n- Item\n\n## Posições declaradas\n\n- Item\n\n## Controvérsias e processos\n\n- **Nov. 2024:** O que aconteceu, e a versão da pessoa\n\n' +
    '## Fontes\n\n- [Título da matéria — Veículo, 4 out. 2026](https://exemplo.com)';

  function escreverFicha(f, corpo) {
    var dados = {};
    ORDEM_FICHA.forEach(function (k) {
      if (k === 'selos') dados.selos = (f.selos || []).filter(function (s) { return s && s.texto; }).map(function (s) { return { texto: s.texto, destaque: !!s.destaque }; });
      else if (k === 'dados') dados.dados = (f.dados || []).filter(function (d) { return d && String(d.valor || '').trim(); }).map(function (d) { return { rotulo: d.rotulo || '', valor: d.valor || '' }; });
      else if (k === 'eleicoes') dados.eleicoes = (f.eleicoes || []).filter(function (e) { return e && (e.ano || e.cargo); }).map(function (e) {
        var ano = parseInt(e.ano, 10);
        return { ano: isNaN(ano) ? String(e.ano || '') : ano, cargo: e.cargo || '', partido: e.partido || '', votos: e.votos || '', resultado: e.resultado || '', destaque: !!e.destaque };
      });
      else dados[k] = f[k] == null ? '' : String(f[k]);
    });
    return escrever(dados, corpo == null ? corpoFicha(f) : corpo, ORDEM_FICHA);
  }

  // =========================================================================
  // Votação (conteudo/votacoes/<id>.md): dados da consulta do e-Cidadania no cabeçalho
  // (recomendacao: "sim" ou "nao"); o texto é a nossa descrição, em Markdown.
  // =========================================================================
  var ORDEM_VOTACAO = ['titulo', 'sigla', 'identificacao', 'autoria', 'ementa', 'ecidadania_id', 'recomendacao',
    'votos_sim', 'votos_nao', 'apurado_em', 'data'];

  function lerVotacao(texto) {
    var r = ler(texto), v = {};
    ORDEM_VOTACAO.forEach(function (k) { v[k] = r.dados[k] == null ? '' : r.dados[k]; });
    ['ecidadania_id', 'votos_sim', 'votos_nao'].forEach(function (k) { var n = parseInt(v[k], 10); v[k] = isNaN(n) ? '' : n; });
    v.recomendacao = v.recomendacao === 'sim' || v.recomendacao === 'nao' ? v.recomendacao : '';
    v.corpo = r.corpo;
    return v;
  }

  function escreverVotacao(v) {
    var dados = {};
    ORDEM_VOTACAO.forEach(function (k) {
      if (k === 'ecidadania_id' || k === 'votos_sim' || k === 'votos_nao') {
        var n = parseInt(v[k], 10);
        dados[k] = isNaN(n) ? 0 : n;
      } else dados[k] = v[k] == null ? '' : String(v[k]);
    });
    return escrever(dados, v.corpo || '', ORDEM_VOTACAO);
  }

  // =========================================================================
  // Vídeo do YouTube (conteudo/videos/<id>.md): só o cabeçalho, sem texto.
  // capa: imagem enviada (imagens/videos/...) ou endereço https da capa do YouTube; foto_criador: foto do canal.
  // =========================================================================
  var ORDEM_VIDEO = ['titulo', 'criador', 'foto_criador', 'link', 'capa', 'data'];

  function lerVideo(texto) {
    var r = ler(texto), v = {};
    ORDEM_VIDEO.forEach(function (k) { v[k] = r.dados[k] == null ? '' : String(r.dados[k]); });
    return v;
  }

  function escreverVideo(v) {
    var dados = {};
    ORDEM_VIDEO.forEach(function (k) { dados[k] = v[k] == null ? '' : String(v[k]).trim(); });
    return escrever(dados, '', ORDEM_VIDEO);
  }

  // =========================================================================
  // Publicação (conteudo/publicacoes/<id>.md): livro ou revista.
  // Cabeçalho: tipo ("livro" ou "revista"), titulo, autoria, editora, ano (livros), edicao, data (revistas),
  // capa (imagens/publicacoes/... ou https://...), link (PDF, leitura ou loja), rotulo_link, assuntos (lista).
  // Texto: a descrição, em Markdown simples (a página mostra só o texto, sem as marcas).
  // =========================================================================
  var ORDEM_PUBLICACAO = ['tipo', 'titulo', 'autoria', 'editora', 'ano', 'edicao', 'data', 'capa', 'link', 'rotulo_link', 'assuntos'];

  function lerPublicacao(texto) {
    var r = ler(texto), p = {};
    ORDEM_PUBLICACAO.forEach(function (k) { p[k] = r.dados[k] == null ? '' : r.dados[k]; });
    p.tipo = p.tipo === 'revista' ? 'revista' : 'livro';
    p.assuntos = Array.isArray(p.assuntos) ? p.assuntos.map(String) : (p.assuntos ? [String(p.assuntos)] : []);
    ORDEM_PUBLICACAO.forEach(function (k) { if (k !== 'assuntos') p[k] = String(p[k]); });
    p.corpo = r.corpo;
    return p;
  }

  function escreverPublicacao(p) {
    var dados = {}, livro = p.tipo !== 'revista';
    ORDEM_PUBLICACAO.forEach(function (k) {
      if (k === 'assuntos') { dados.assuntos = (p.assuntos || []).filter(Boolean); return; }
      if (livro && (k === 'edicao' || k === 'data')) return;      // campos só de revista
      if (!livro && (k === 'autoria' || k === 'editora' || k === 'ano')) return;   // campos só de livro
      dados[k] = p[k] == null ? '' : String(p[k]).trim();
    });
    dados.tipo = livro ? 'livro' : 'revista';
    return escrever(dados, p.corpo || '', ORDEM_PUBLICACAO);
  }

  // =========================================================================
  // Dossiê (conteudo/dossies/<id>.md): reportagem longa, dividida em capítulos.
  // Cabeçalho: titulo, linha (subtítulo), data, editado (opcional), autor, capa, legenda, credito, tags, destaque.
  // Texto: Markdown; cada "## Título" abre um capítulo. O que vem antes do primeiro "## " é a apresentação.
  // =========================================================================
  var ORDEM_DOSSIE = ['titulo', 'linha', 'data', 'editado', 'autor', 'capa', 'legenda', 'credito', 'tags', 'destaque'];

  function lerDossie(texto) {
    var r = ler(texto), d = {};
    ORDEM_DOSSIE.forEach(function (k) { d[k] = r.dados[k] == null ? '' : r.dados[k]; });
    d.tags = Array.isArray(d.tags) ? d.tags.map(String) : (d.tags ? [String(d.tags)] : []);
    d.destaque = d.destaque === true;
    ORDEM_DOSSIE.forEach(function (k) { if (k !== 'tags' && k !== 'destaque') d[k] = String(d[k]); });
    d.corpo = r.corpo;
    return d;
  }

  function escreverDossie(d) {
    var dados = {};
    ORDEM_DOSSIE.forEach(function (k) {
      if (k === 'tags') dados.tags = (d.tags || []).filter(Boolean);
      else if (k === 'destaque') dados.destaque = !!d.destaque;
      else if (k === 'editado') { if (d.editado) dados.editado = String(d.editado); }
      else dados[k] = d[k] == null ? '' : String(d[k]).trim();
    });
    return escrever(dados, d.corpo || '', ORDEM_DOSSIE);
  }

  // Texto sem as marcas de Markdown (títulos do sumário)
  function textoSimples(t) {
    return String(t || '').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').replace(/(\*\*|__|\*|_)(.+?)\1/g, '$2').trim();
  }

  // Divide o texto do dossiê: { apresentacao: md, capitulos: [{ n, titulo, ancora, corpo }] }
  function capitulosDossie(md) {
    var apresentacao = [], capitulos = [], atual = null, usadas = {};
    String(md || '').replace(/\r/g, '').split('\n').forEach(function (linha) {
      var m = linha.match(/^##\s+(.*)$/);
      if (m) {
        var titulo = textoSimples(m[1]);
        var base = chave(titulo).replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'capitulo';
        var ancora = base, n = 2;
        while (usadas[ancora]) ancora = base + '-' + (n++);
        usadas[ancora] = true;
        atual = { n: capitulos.length + 1, titulo: titulo, ancora: ancora, linhas: [] };
        capitulos.push(atual);
        return;
      }
      (atual ? atual.linhas : apresentacao).push(linha);
    });
    return {
      apresentacao: apresentacao.join('\n').trim(),
      capitulos: capitulos.map(function (c) { return { n: c.n, titulo: c.titulo, ancora: c.ancora, corpo: c.linhas.join('\n').trim() }; })
    };
  }

  window.TCMarkdown = {
    lerDossie: lerDossie, escreverDossie: escreverDossie, capitulosDossie: capitulosDossie, textoSimples: textoSimples,
    lerPublicacao: lerPublicacao, escreverPublicacao: escreverPublicacao,
    ler: ler, escrever: escrever, inline: inline, blocos: blocos, html: html, caminhoImagem: caminhoImagem,
    lerMateria: lerMateria, escreverMateria: escreverMateria,
    lerFicha: lerFicha, escreverFicha: escreverFicha, corpoFicha: corpoFicha, MODELO_FICHA: MODELO_FICHA,
    lerVotacao: lerVotacao, escreverVotacao: escreverVotacao,
    lerVideo: lerVideo, escreverVideo: escreverVideo
  };
})();
