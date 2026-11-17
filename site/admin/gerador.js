/* Tempo Continuum — Gerador de imagens (dentro do editor).
   O desenho é feito pelo motor em Rust compilado para WebAssembly (js/motor/, fonte em ../motor-imagens/),
   no navegador: nada é enviado ao servidor. Este arquivo cuida só da interface.
   Os formatos ficam em dados/layouts-imagens.json.

   Uso:
     TCGerador.montar(elemento, { chave: 'tc-gerador-imagens' })          // livre: tudo digitado à mão
     var g = TCGerador.montar(elemento, { automatico: true, memoria: {}, item: 'noticias/id', rotulo: 'da matéria' });
     g.preencher({ titulo, selo, rodape1, rodape2, link, nome, fundo: 'caminho ou https://…', logos: ['caminho', …], aviso })
   No modo automático, cada campo segue o que vier em preencher() até ser editado à mão no gerador;
   o botão "↺" ao lado do campo volta a seguir o item. */
(function () {
  'use strict';

  var RAIZ = new URL('../', (document.currentScript && document.currentScript.src) || location.href).href;
  var MAX_LINHAS_OPCAO = 8;   // até quantas linhas o seletor oferece
  var LADO_MAX_FOTO = 4096;   // fotos maiores são reduzidas antes de ir para o motor
  var ALTURA_MIN_LOGO = 600;  // logos em SVG são rasterizadas pelo menos nesta altura
  var CHAVE_ITENS = 'tc-gerador-itens', MAX_ITENS = 200;
  var CAMPOS = ['titulo', 'selo', 'rodape1', 'rodape2', 'link', 'nome'];

  // =========================================================================
  // Motor (WebAssembly) e formatos: carregados uma vez só, para todas as montagens
  // =========================================================================
  var motor = null, promessaMotor = null, promessaLayouts = null, proximoNome = 0;
  function carregarMotor() {
    if (!promessaMotor) promessaMotor = import(RAIZ + 'js/motor/motor_imagens.js').then(function (m) {
      return m.default().then(function () { motor = new m.Motor(); return motor; });
    });
    return promessaMotor;
  }
  function carregarLayouts() {
    if (!promessaLayouts) promessaLayouts = fetch(RAIZ + 'dados/layouts-imagens.json', { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (j) { return j.layouts; });
    promessaLayouts.catch(function () { promessaLayouts = null; });
    return promessaLayouts;
  }

  // Converte uma imagem do navegador em pixels RGBA e entrega ao motor com o nome dado
  function enviarImagem(nome, img, tipo) {
    var w = img.naturalWidth || img.width, h = img.naturalHeight || img.height;
    if (!w || !h) { w = 300; h = 100; }   // SVG sem tamanho declarado
    var k = Math.min(1, LADO_MAX_FOTO / Math.max(w, h));
    if (tipo === 'image/svg+xml' && h * k < ALTURA_MIN_LOGO) k = Math.min(ALTURA_MIN_LOGO / h, LADO_MAX_FOTO / Math.max(w, h));
    var tela = document.createElement('canvas');
    tela.width = Math.max(1, Math.round(w * k)); tela.height = Math.max(1, Math.round(h * k));
    var ctx = tela.getContext('2d');
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(img, 0, 0, tela.width, tela.height);
    var px = ctx.getImageData(0, 0, tela.width, tela.height).data;
    motor.definir_imagem(nome, tela.width, tela.height, new Uint8Array(px.buffer, px.byteOffset, px.byteLength));
  }

  function renderizar(canvas, L, D, op) {
    op = op || {};
    var r = motor.renderizar(JSON.stringify(L), JSON.stringify(D), op.escala || 1, !!op.guias);
    try {
      var px = r.pixels;
      canvas.width = r.largura; canvas.height = r.altura;
      canvas.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(px.buffer, px.byteOffset, px.byteLength), r.largura, r.altura), 0, 0);
      return JSON.parse(r.relatorio);
    } finally { r.free(); }
  }

  function aplicarAjustes(L, ajustes) {
    var aj = (ajustes && ajustes[L.nome]) || {};
    var camadas = [];
    (L.camadas || []).forEach(function (c, i) {
      var a = aj[i] || {};
      if (a.visivel === false) return;
      var nova = Object.assign({}, c);
      if (a.alpha != null) nova.alpha = a.alpha;
      if (a.alpha2 != null) nova.alpha2 = a.alpha2;
      camadas.push(nova);
    });
    return Object.assign({}, L, { camadas: camadas });
  }

  // Imagens abertas por endereço (foto do item, logo padrão): guardadas para não recarregar a cada redesenho do formulário
  var porEndereco = {};
  function enderecoCompleto(src) {
    if (/^(https?:|data:|blob:)/.test(src)) return src;
    return RAIZ + String(src).replace(/^(\.\.\/|\/)+/, '');
  }
  function carregarImg(url, cruzada) {
    return new Promise(function (ok, falha) {
      var img = new Image();
      if (cruzada) img.crossOrigin = 'anonymous';
      img.onload = function () { ok(img); };
      img.onerror = function () { falha(new Error('não consegui abrir a imagem')); };
      img.src = url;
    });
  }
  // Foto de outro site: o navegador só deixa desenhá-la se vier da mesma origem,
  // então ela é buscada pelo servidor local (scripts/servidor.py, /api/imagem-externa)
  function buscarExterna(url) {
    return fetch(RAIZ + 'api/imagem-externa?url=' + encodeURIComponent(url), { headers: { 'X-TC-Editor': '1' } }).then(function (r) {
      if (!r.ok) return r.json().catch(function () { return {}; }).then(function (j) { throw new Error(j.erro || 'HTTP ' + r.status); });
      return r.blob();
    }).then(function (b) { return carregarImg(URL.createObjectURL(b), false); });
  }
  function abrirEndereco(src) {
    var url = enderecoCompleto(src), externa = /^https?:/.test(url) && url.indexOf(location.origin + '/') !== 0;
    if (!porEndereco[url]) {
      porEndereco[url] = externa
        ? buscarExterna(url).catch(function (e) {
            return carregarImg(url, true).catch(function () {
              throw new Error('não consegui trazer a foto do outro site (' + e.message + '). Envie a foto pelo editor ("Enviar imagem") ou abra-a aqui no gerador');
            });
          })
        : carregarImg(url, false).catch(function () { throw new Error('não consegui abrir ' + src); });
      porEndereco[url].catch(function () { delete porEndereco[url]; });
    }
    return porEndereco[url];
  }
  function tipoDoEndereco(src) { return /\.svg(\?|#|$)/i.test(src) ? 'image/svg+xml' : ''; }
  function nomeDoEndereco(src) { return decodeURIComponent(String(src).split(/[?#]/)[0].split('/').pop() || src); }

  function semAcento(s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, ''); }

  // Memória por item (ajustes feitos à mão no gerador de uma matéria), neste navegador
  function lerItens() { try { return JSON.parse(localStorage.getItem(CHAVE_ITENS) || '{}'); } catch (e) { return {}; } }
  function gravarItem(item, dados) {
    if (!item) return;
    var t = lerItens();
    if (!dados && !(item in t)) return;
    delete t[item];
    if (dados) t[item] = dados;
    var ks = Object.keys(t);
    while (ks.length > MAX_ITENS) delete t[ks.shift()];
    try { localStorage.setItem(CHAVE_ITENS, JSON.stringify(t)); } catch (e) {}
  }

  // =========================================================================
  // Interface
  // =========================================================================
  var HTML =
    '<div class="gr-controles">' +
    '<fieldset class="gr-grupo"><legend>Formato e texto</legend>' +
      '<p class="gr-dica" data-g="explica" hidden></p>' +
      '<label class="gr-campo">Formato<select data-g="formato"></select></label>' +
      '<label class="gr-campo"><span class="gr-rotulo"><span>Título</span><span data-g="contador"></span></span>' +
        '<textarea data-g="titulo" rows="3" placeholder="Escreva o título; ele se ajusta à área"></textarea></label>' +
      '<label class="gr-campo">Linhas do título<select data-g="linhas"></select>' +
        '<span class="gr-dica">Escolha um número para limitar o título: a fonte diminui até ele caber nessas linhas.</span></label>' +
      '<label class="gr-campo"><span class="gr-rotulo"><span>Selo (opcional)</span></span><input type="text" data-g="selo" placeholder="Ex.: Urgente, Análise"></label>' +
      '<div class="gr-dupla">' +
        '<label class="gr-campo"><span class="gr-rotulo"><span>Rodapé, linha em destaque</span></span><input type="text" data-g="rodape1" placeholder="Ex.: Leia a matéria completa"></label>' +
        '<label class="gr-campo"><span class="gr-rotulo"><span>Rodapé, segunda linha</span></span><input type="text" data-g="rodape2" placeholder="Ex.: seusite.org"></label>' +
      '</div>' +
      '<label class="gr-campo"><span class="gr-rotulo"><span>Link do QR code (opcional)</span></span><input type="url" data-g="link" placeholder="https://…" inputmode="url"></label>' +
    '</fieldset>' +
    '<fieldset class="gr-grupo"><legend>Imagem de fundo</legend>' +
      '<div class="gr-zona" data-g="zona" tabindex="0" role="button" aria-label="Escolher imagem de fundo">' +
        '<span class="gr-vazio" data-g="fundo-vazio" aria-hidden="true">+</span><img data-g="fundo-mini" alt="" hidden>' +
        '<span data-g="fundo-nome">Clique ou arraste uma imagem</span></div>' +
      '<input type="file" data-g="arquivo-fundo" accept="image/*" hidden>' +
      '<div class="gr-dupla">' +
        '<label class="gr-campo"><span class="gr-rotulo"><span>Foco horizontal</span><span data-g="focoX-v"></span></span><input type="range" data-g="focoX" min="0" max="100" step="1"></label>' +
        '<label class="gr-campo"><span class="gr-rotulo"><span>Foco vertical</span><span data-g="focoY-v"></span></span><input type="range" data-g="focoY" min="0" max="100" step="1"></label>' +
      '</div>' +
      '<div class="gr-linha-botoes"><button type="button" data-g="remover-fundo" hidden>Remover fundo</button>' +
      '<button type="button" data-g="voltar-fundo" hidden></button></div>' +
    '</fieldset>' +
    '<fieldset class="gr-grupo"><legend>Logos (opcional)</legend>' +
      '<div data-g="logos" class="gr-lista"></div>' +
      '<div class="gr-linha-botoes"><button type="button" data-g="adicionar-logo">+ Adicionar logo</button>' +
      '<button type="button" data-g="voltar-logos" hidden>↺ Usar a logo padrão</button></div>' +
      '<input type="file" data-g="arquivo-logo" accept="image/*" multiple hidden>' +
      '<p class="gr-dica">Ficam na faixa de logos do formato e diminuem juntas se não couberem. PNG com fundo transparente funciona melhor.</p>' +
    '</fieldset>' +
    '<details class="gr-grupo"><summary>Camadas e transparência</summary><div>' +
      '<div data-g="camadas" class="gr-lista"></div>' +
      '<button type="button" data-g="restaurar">Restaurar camadas do formato</button>' +
      '<p class="gr-dica">Os ajustes valem só para o formato selecionado.</p>' +
    '</div></details>' +
    '<fieldset class="gr-grupo"><legend>Baixar</legend>' +
      '<label class="gr-campo"><span class="gr-rotulo"><span>Nome do arquivo (opcional)</span></span><input type="text" data-g="nome" placeholder="Automático, a partir do título"></label>' +
      '<label class="gr-campo">Resolução<select data-g="escala"><option value="1">Padrão</option><option value="2">2× (mais nítida)</option></select></label>' +
      '<button type="button" class="gr-principal" data-g="baixar">Baixar PNG</button>' +
      '<button type="button" data-g="baixar-todos">Baixar em todos os formatos</button>' +
      '<button type="button" data-g="recomecar"></button>' +
      '<p class="gr-dica" data-g="nota"></p>' +
    '</fieldset>' +
    '</div>' +
    '<div class="gr-palco">' +
      '<div class="gr-quadro" data-g="quadro"><canvas data-g="previa" role="img" aria-label="Prévia da imagem"></canvas></div>' +
      '<div class="gr-barra"><span data-g="medidas"></span>' +
        '<label class="gr-checar"><input type="checkbox" data-g="guias"> Mostrar áreas demarcadas</label></div>' +
      '<div class="gr-relatorio" data-g="relatorio" aria-live="polite"></div>' +
    '</div>';

  function montar(lugar, op) {
    op = op || {};
    var auto = !!op.automatico;
    var CHAVE = op.chave || (auto ? 'tc-gerador-editor' : 'tc-gerador-imagens');
    var raiz = document.createElement('div');
    raiz.className = 'gr';
    raiz.innerHTML = HTML;
    lugar.appendChild(raiz);
    var $ = function (k) { return raiz.querySelector('[data-g="' + k + '"]'); };

    var LAYOUTS = [], porNome = {};
    var imagens = { fundo: null, fundoNome: '', fundoSrc: '', logos: [] };
    // Em modo automático, só formato, linhas, escala, guias e camadas ficam na chave geral;
    // os textos vêm do item, e o que for editado à mão fica na memória do item.
    var estado = {
      layout: 'post-retrato', titulo: auto ? '' : 'Escreva aqui o título: ele se ajusta sozinho à área demarcada',
      selo: '', rodape1: '', rodape2: '', link: '', nome: '',
      focoX: 50, focoY: 50, escala: 1, guias: false, ajustes: {}, linhas: 0
    };
    var GERAIS = ['layout', 'escala', 'guias', 'ajustes', 'linhas'];
    try {
      var salvo = JSON.parse(localStorage.getItem(CHAVE) || '{}');
      Object.keys(salvo).forEach(function (k) { if (!auto || GERAIS.indexOf(k) >= 0) estado[k] = salvo[k]; });
    } catch (e) {}
    // Memória do item: { manual: {campo: true}, valores: {campo: texto}, focoX, focoY }
    var mem = op.memoria || {};
    if (auto && !mem.manual) {
      var guardado = op.item ? lerItens()[op.item] : null;
      mem.manual = (guardado && guardado.manual) || {};
      mem.valores = (guardado && guardado.valores) || {};
      if (guardado && guardado.focoX != null) { mem.focoX = guardado.focoX; mem.focoY = guardado.focoY; }
    }
    if (auto) {
      CAMPOS.forEach(function (k) { if (mem.manual[k] && mem.valores[k] != null) estado[k] = mem.valores[k]; });
      if (mem.focoX != null) { estado.focoX = mem.focoX; estado.focoY = mem.focoY; }
    }
    var vindo = {};   // último preencher(): o que o item oferece para cada campo

    function guardar() {
      var geral = {};
      if (auto) GERAIS.forEach(function (k) { geral[k] = estado[k]; }); else geral = estado;
      try { localStorage.setItem(CHAVE, JSON.stringify(geral)); } catch (e) {}
      if (auto) {
        mem.focoX = estado.focoX; mem.focoY = estado.focoY;
        CAMPOS.forEach(function (k) { if (mem.manual[k]) mem.valores[k] = estado[k]; else delete mem.valores[k]; });
        var temAlgo = Object.keys(mem.manual).some(function (k) { return mem.manual[k]; }) || mem.focoX !== 50 || mem.focoY !== 50;
        if (op.item) gravarItem(op.item, temAlgo ? { manual: mem.manual, valores: mem.valores, focoX: mem.focoX, focoY: mem.focoY } : null);
      }
    }

    function dados() {
      return {
        titulo: estado.titulo, linhasTitulo: estado.linhas, selo: estado.selo, rodape: [estado.rodape1, estado.rodape2],
        link: estado.link, fundo: imagens.fundo ? imagens.fundo.nome : null, focoX: estado.focoX, focoY: estado.focoY,
        logos: imagens.logos.map(function (l) { return l.id; })
      };
    }
    function layoutAtual() { return aplicarAjustes(porNome[estado.layout], estado.ajustes); }
    function vivo() { return raiz.isConnected; }

    // ---- Prévia
    var previa = $('previa'), quadro = $('quadro'), agendado = false, ultimoAviso = null;
    function agendar() {
      guardar();
      if (agendado) return;
      agendado = true;
      requestAnimationFrame(function () { agendado = false; desenharPrevia(); });
    }
    function desenharPrevia() {
      if (!LAYOUTS.length || !motor || !vivo()) return;
      // Garante que as imagens desta montagem estão no motor (outra montagem pode ter usado os mesmos nomes antes)
      if (imagens.fundo && !imagens.fundo.enviada) { enviarImagem(imagens.fundo.nome, imagens.fundo.img, imagens.fundo.tipo); imagens.fundo.enviada = true; }
      imagens.logos.forEach(function (l) { if (!l.enviada) { enviarImagem(l.id, l.img, l.tipo); l.enviada = true; } });
      var L = layoutAtual();
      var estreita = window.innerWidth < 860;
      var maxW = quadro.clientWidth - (estreita ? 0 : 40);
      var maxH = estreita ? Math.max(220, window.innerHeight * 0.42) : Math.max(320, Math.min(window.innerHeight * 0.7, 900));
      if (maxW <= 0) return;
      var disp = Math.min(maxW / L.largura, maxH / L.altura);
      previa.style.width = Math.floor(L.largura * disp) + 'px';
      previa.style.height = Math.floor(L.altura * disp) + 'px';
      var esc = Math.min(1, disp * (window.devicePixelRatio || 1));
      var rel = renderizar(previa, L, dados(), { escala: esc, guias: estado.guias });
      var ex = tamanhoExportado(L, 1);
      $('medidas').textContent = 'Exporta em ' + ex.largura + ' × ' + ex.altura + ' px';
      relatorio(rel, ultimoAviso);
    }
    function relatorio(rel, extra) {
      var caixa = $('relatorio');
      caixa.innerHTML = '';
      function add(t, cls) { var d = document.createElement('p'); d.textContent = t; if (cls) d.className = cls; caixa.appendChild(d); }
      if (rel && rel.titulo) add('Título em ' + Math.round(rel.titulo.fonte) + ' px, ' + rel.titulo.linhas + (rel.titulo.linhas === 1 ? ' linha' : ' linhas') + ' (máximo ' + rel.titulo.limite + ').');
      (rel && rel.avisos || []).forEach(function (a) { add('Atenção: ' + a + '.', 'gr-aviso'); });
      if (auto && vindo.aviso) add(vindo.aviso, 'gr-dica-rel');
      if (extra) add(extra.t, extra.cls);
    }
    function avisar(t, cls) { ultimoAviso = t ? { t: t, cls: cls } : null; relatorio(null, ultimoAviso); agendar(); }
    function aoRedimensionar() { if (!vivo()) { window.removeEventListener('resize', aoRedimensionar); return; } agendar(); }
    window.addEventListener('resize', aoRedimensionar);

    // ---- Campos de texto (no modo automático, com a marca "da matéria" ou o botão para voltar a segui-la)
    var marcas = {};
    function marcar(k) {
      var m = marcas[k];
      if (!m) return;
      if (mem.manual[k]) {
        m.textContent = '↺ ' + (op.rotulo || 'do item');
        m.title = 'Editado aqui. Clique para voltar a usar o que está ' + (op.rotulo || 'no item');
        m.className = 'gr-origem gr-solto';
        m.disabled = false;
      } else {
        m.textContent = op.rotulo || 'do item';
        m.title = 'Preenchido sozinho; muda junto com o item';
        m.className = 'gr-origem';
        m.disabled = true;
      }
    }
    function ligar(k) {
      var el = $(k);
      el.value = estado[k] == null ? '' : estado[k];
      el.addEventListener('input', function () {
        estado[k] = el.value;
        if (auto) { mem.manual[k] = true; marcar(k); }
        if (k === 'titulo') contar();
        agendar();
      });
      if (auto) {
        var linha = el.closest('label').querySelector('.gr-rotulo');
        var b = document.createElement('button');
        b.type = 'button';
        b.addEventListener('click', function (ev) {
          ev.preventDefault();
          mem.manual[k] = false;
          estado[k] = vindo[k] == null ? '' : vindo[k];
          el.value = estado[k];
          marcar(k); if (k === 'titulo') contar(); agendar();
        });
        if (k === 'titulo') linha.insertBefore(b, linha.lastChild); else linha.appendChild(b);
        marcas[k] = b;
        marcar(k);
      }
    }
    function contar() { $('contador').textContent = estado.titulo.length + ' caracteres'; }
    CAMPOS.forEach(ligar);
    contar();

    $('formato').addEventListener('change', function (ev) { estado.layout = ev.target.value; desenharCamadas(); opcoesLinhas(); opcoesEscala(); agendar(); });

    function opcoesLinhas() {
      var sel = $('linhas'), L = porNome[estado.layout];
      sel.innerHTML = '';
      var o0 = document.createElement('option');
      o0.value = '0'; o0.textContent = 'Automático (até ' + L.titulo.max_linhas + ' neste formato)';
      sel.appendChild(o0);
      for (var n = 1; n <= MAX_LINHAS_OPCAO; n++) {
        var o = document.createElement('option');
        o.value = String(n); o.textContent = n === 1 ? '1 linha' : 'Até ' + n + ' linhas';
        sel.appendChild(o);
      }
      sel.value = String(estado.linhas || 0);
    }
    $('linhas').addEventListener('change', function (ev) { estado.linhas = +ev.target.value; agendar(); });
    $('guias').checked = !!estado.guias;
    $('guias').addEventListener('change', function (ev) { estado.guias = ev.target.checked; agendar(); });
    function tamanhoExportado(L, mult) {
      var base = L.exportar || { largura: L.largura, altura: L.altura };
      return { largura: Math.round(base.largura * mult), altura: Math.round(base.altura * mult), escala: base.largura / L.largura * mult };
    }
    function opcoesEscala() {
      var L = porNome[estado.layout], sel = $('escala');
      [1, 2].forEach(function (m, i) {
        var t = tamanhoExportado(L, m);
        sel.options[i].textContent = (m === 1 ? 'Padrão' : '2× (mais nítida)') + ' · ' + t.largura + ' × ' + t.altura + ' px';
      });
    }
    $('escala').value = String(estado.escala);
    $('escala').addEventListener('change', function (ev) { estado.escala = +ev.target.value; guardar(); });

    // ---- Abrir imagens do computador
    function abrirArquivo(arquivo) {
      return new Promise(function (ok, falha) {
        if (!arquivo || !/^image\//.test(arquivo.type)) return falha(new Error('escolha um arquivo de imagem'));
        var img = new Image();
        img.onload = function () { ok(img); };
        img.onerror = function () { falha(new Error('não consegui abrir ' + arquivo.name)); };
        img.src = URL.createObjectURL(arquivo);
      });
    }

    // ---- Fundo
    function mostrarFundo() {
      var tem = !!imagens.fundo;
      $('fundo-mini').hidden = !tem;
      $('fundo-vazio').hidden = tem;
      if (tem) $('fundo-mini').src = imagens.fundo.img.src;
      $('fundo-nome').textContent = tem ? imagens.fundoNome : 'Clique ou arraste uma imagem';
      $('remover-fundo').hidden = !tem;
      var vb = $('voltar-fundo');
      vb.hidden = !(auto && mem.manual.fundo);
      vb.textContent = vindo.fundo ? '↺ Usar a foto ' + (op.rotulo || 'do item') : '↺ Sem fundo, como ' + (op.rotulo || 'o item');
    }
    function definirFundo(img, nomeExibido, tipo, src) {
      imagens.fundo = { img: img, nome: 'fundo-' + (proximoNome++), tipo: tipo, enviada: false };
      imagens.fundoNome = nomeExibido; imagens.fundoSrc = src || '';
      mostrarFundo(); agendar();
    }
    function semFundo() { imagens.fundo = null; imagens.fundoNome = ''; imagens.fundoSrc = ''; mostrarFundo(); agendar(); }
    function usarArquivoFundo(arq) {
      abrirArquivo(arq).then(function (img) {
        if (auto) mem.manual.fundo = true;
        definirFundo(img, arq.name, arq.type, '');
      }).catch(function (e) { avisar(e.message, 'gr-erro'); });
    }
    var fundoPedido = null;   // último endereço pedido (não repete o pedido a cada tecla)
    function fundoDoItem() {
      var src = vindo.fundo || '';
      if (src === fundoPedido) return;
      fundoPedido = src;
      if (!src) { semFundo(); return; }
      abrirEndereco(src).then(function (img) {
        if (mem.manual.fundo || vindo.fundo !== src) return;   // mudou enquanto carregava
        definirFundo(img, nomeDoEndereco(src), tipoDoEndereco(src), src);
        if (ultimoAviso && ultimoAviso.fundo) avisar(null);
      }, function (e) {
        if (vindo.fundo !== src) return;
        semFundo();
        ultimoAviso = { t: 'Fundo: ' + e.message + '.', cls: 'gr-aviso', fundo: true };
        agendar();
      });
    }
    var zona = $('zona');
    zona.addEventListener('click', function () { $('arquivo-fundo').click(); });
    zona.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); $('arquivo-fundo').click(); } });
    $('arquivo-fundo').addEventListener('change', function (ev) { if (ev.target.files[0]) usarArquivoFundo(ev.target.files[0]); ev.target.value = ''; });
    ['dragenter', 'dragover'].forEach(function (t) { zona.addEventListener(t, function (ev) { ev.preventDefault(); zona.classList.add('gr-arrastando'); }); });
    ['dragleave', 'drop'].forEach(function (t) { zona.addEventListener(t, function (ev) { ev.preventDefault(); zona.classList.remove('gr-arrastando'); }); });
    zona.addEventListener('drop', function (ev) { if (ev.dataTransfer.files[0]) usarArquivoFundo(ev.dataTransfer.files[0]); });
    $('remover-fundo').addEventListener('click', function () { if (auto) mem.manual.fundo = true; semFundo(); });
    $('voltar-fundo').addEventListener('click', function () { mem.manual.fundo = false; fundoPedido = null; fundoDoItem(); mostrarFundo(); });
    ['X', 'Y'].forEach(function (eixo) {
      var el = $('foco' + eixo), saida = $('foco' + eixo + '-v');
      el.value = estado['foco' + eixo];
      saida.textContent = el.value + '%';
      el.addEventListener('input', function () { estado['foco' + eixo] = +el.value; saida.textContent = el.value + '%'; agendar(); });
    });

    // ---- Logos
    function desenharLogos() {
      var lista = $('logos');
      lista.innerHTML = '';
      $('voltar-logos').hidden = !(auto && mem.manual.logos && (vindo.logos || []).length);
      if (!imagens.logos.length) { lista.innerHTML = '<p class="gr-dica">Nenhuma logo. Adicione as suas, se quiser.</p>'; return; }
      imagens.logos.forEach(function (l, i) {
        var item = document.createElement('div');
        item.className = 'gr-item';
        var mini = document.createElement('img'); mini.src = l.img.src; mini.alt = '';
        var nome = document.createElement('span'); nome.className = 'gr-item-nome'; nome.textContent = l.nome;
        var acoes = document.createElement('span'); acoes.className = 'gr-item-acoes';
        [['←', 'Mover para a esquerda', -1], ['→', 'Mover para a direita', 1], ['✕', 'Remover logo', 0]].forEach(function (b) {
          var bt = document.createElement('button');
          bt.type = 'button'; bt.textContent = b[0]; bt.setAttribute('aria-label', b[1] + ': ' + l.nome);
          bt.addEventListener('click', function () {
            var L = imagens.logos, j = i + b[2];
            if (b[2] === 0) L.splice(i, 1);
            else if (j >= 0 && j < L.length) { var t = L[i]; L[i] = L[j]; L[j] = t; }
            if (auto) mem.manual.logos = true;
            desenharLogos(); agendar();
          });
          acoes.appendChild(bt);
        });
        item.appendChild(mini); item.appendChild(nome); item.appendChild(acoes);
        lista.appendChild(item);
      });
    }
    function novaLogo(img, nome, tipo, src) { return { img: img, nome: nome, id: 'logo-' + (proximoNome++), tipo: tipo, src: src || '', enviada: false }; }
    $('adicionar-logo').addEventListener('click', function () { $('arquivo-logo').click(); });
    $('arquivo-logo').addEventListener('change', function (ev) {
      var arquivos = Array.prototype.slice.call(ev.target.files);
      ev.target.value = '';
      Promise.all(arquivos.map(function (a) {
        return abrirArquivo(a).then(function (img) { return novaLogo(img, a.name, a.type); });
      })).then(function (novas) {
        if (auto) mem.manual.logos = true;
        imagens.logos = imagens.logos.concat(novas); desenharLogos(); agendar();
      }).catch(function (e) { avisar(e.message, 'gr-erro'); });
    });
    var logosVindas = '';
    function logosDoItem(forcar) {
      var lista = vindo.logos || [], chave = lista.join('|');
      if (!forcar && chave === logosVindas) return;
      logosVindas = chave;
      Promise.all(lista.map(function (src) {
        return abrirEndereco(src).then(function (img) { return novaLogo(img, nomeDoEndereco(src), tipoDoEndereco(src), src); }, function () { return null; });
      })).then(function (ls) {
        if (mem.manual.logos || logosVindas !== chave) return;
        imagens.logos = ls.filter(Boolean); desenharLogos(); agendar();
      });
    }
    $('voltar-logos').addEventListener('click', function () { mem.manual.logos = false; logosDoItem(true); desenharLogos(); });

    // ---- Camadas
    var TIPOS = { cor: 'Cor', gradiente: 'Gradiente' };
    function desenharCamadas() {
      var L = porNome[estado.layout], aj = estado.ajustes[L.nome] || (estado.ajustes[L.nome] = {});
      var lista = $('camadas');
      lista.innerHTML = '';
      L.camadas.forEach(function (c, i) {
        var a = aj[i] || {}, visivel = a.visivel !== false;
        var item = document.createElement('div');
        item.className = 'gr-camada' + (visivel ? '' : ' gr-oculta');
        var topo = document.createElement('label');
        topo.className = 'gr-camada-topo';
        var caixa = document.createElement('input'); caixa.type = 'checkbox'; caixa.checked = visivel;
        var amostra = document.createElement('span'); amostra.className = 'gr-amostra';
        amostra.style.background = c.tipo === 'gradiente' ? 'linear-gradient(' + c.cor + ',' + (c.cor2 || c.cor) + ')' : c.cor;
        var nome = document.createElement('span');
        nome.textContent = (i + 1) + '. ' + (TIPOS[c.tipo] || c.tipo) + ' · ' + c.largura + '×' + c.altura + (c.desfoque ? ' · vidro' : '');
        topo.appendChild(caixa); topo.appendChild(amostra); topo.appendChild(nome);
        item.appendChild(topo);
        caixa.addEventListener('change', function () {
          aj[i] = aj[i] || {};
          if (caixa.checked) delete aj[i].visivel; else aj[i].visivel = false;
          item.classList.toggle('gr-oculta', !caixa.checked);
          agendar();
        });
        var campos = c.tipo === 'gradiente' ? [['alpha', 'Início'], ['alpha2', 'Fim']] : [['alpha', 'Opacidade']];
        campos.forEach(function (cp) {
          var v = a[cp[0]] != null ? a[cp[0]] : (c[cp[0]] != null ? c[cp[0]] : (cp[0] === 'alpha2' ? 0 : 1));
          var linha = document.createElement('label'); linha.className = 'gr-slider';
          var rot = document.createElement('span'); rot.textContent = cp[1];
          var r = document.createElement('input'); r.type = 'range'; r.min = 0; r.max = 1; r.step = 0.01; r.value = v;
          var out = document.createElement('span'); out.textContent = Math.round(v * 100) + '%';
          r.addEventListener('input', function () {
            (aj[i] = aj[i] || {})[cp[0]] = +r.value;
            out.textContent = Math.round(r.value * 100) + '%';
            agendar();
          });
          linha.appendChild(rot); linha.appendChild(r); linha.appendChild(out);
          item.appendChild(linha);
        });
        lista.appendChild(item);
      });
    }
    $('restaurar').addEventListener('click', function () { estado.ajustes[estado.layout] = {}; desenharCamadas(); agendar(); });

    // ---- Baixar
    function nomeArquivo(L) {
      var base = semAcento(estado.nome || estado.titulo || 'imagem')
        .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'imagem';
      var t = tamanhoExportado(L, estado.escala);
      return base + '-' + L.nome + '-' + t.largura + 'x' + t.altura + '.png';
    }
    function baixar(nomeLayout) {
      if (!motor) return Promise.reject(new Error('o gerador ainda está carregando'));
      if (!String(estado.titulo).trim()) return Promise.reject(new Error('a imagem está sem título'));
      var L = aplicarAjustes(porNome[nomeLayout], estado.ajustes);
      var tela = document.createElement('canvas'), rel;
      try { rel = renderizar(tela, L, dados(), { escala: tamanhoExportado(L, estado.escala).escala }); }
      catch (e) { return Promise.reject(new Error('não consegui montar a imagem (' + (e.message || e) + ')')); }
      return new Promise(function (ok, falha) {
        tela.toBlob(function (blob) {
          if (!blob) return falha(new Error('o navegador não conseguiu gerar o PNG'));
          var a = document.createElement('a'), nome = nomeArquivo(L);
          a.href = URL.createObjectURL(blob); a.download = nome;
          document.body.appendChild(a); a.click(); a.remove();
          setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
          ok({ nome: nome, rel: rel });
        }, 'image/png');
      });
    }
    $('baixar').addEventListener('click', function () {
      baixar(estado.layout).then(function (r) { ultimoAviso = { t: 'Baixado: ' + r.nome, cls: 'gr-ok' }; relatorio(r.rel, ultimoAviso); },
        function (e) { avisar('Não baixou: ' + e.message + '.', 'gr-erro'); });
    });
    $('baixar-todos').addEventListener('click', function () {
      var nomes = [], cadeia = Promise.resolve();
      LAYOUTS.forEach(function (L) {
        cadeia = cadeia.then(function () { return baixar(L.nome); })
          .then(function (r) { nomes.push(r.nome); return new Promise(function (ok) { setTimeout(ok, 350); }); });
      });
      cadeia.then(function () { avisar('Baixados: ' + nomes.join(', '), 'gr-ok'); },
        function (e) { avisar('Não baixou: ' + e.message + '.', 'gr-erro'); });
    });
    var recomecar = $('recomecar');
    if (auto) {
      recomecar.textContent = '↺ Preencher tudo de novo ' + (op.rotulo || 'com o item');
      $('nota').textContent = 'Tudo aqui se preenche sozinho com o que está ' + (op.rotulo || 'no item').replace(/^d/, 'n') +
        ' e muda enquanto você escreve. Se editar um campo aqui, ele para de acompanhar; o botão ↺ ao lado do campo volta a ligá-lo. Nada disso é salvo no arquivo.';
      recomecar.addEventListener('click', function () {
        mem.manual = {}; mem.valores = {};
        estado.focoX = estado.focoY = 50;
        ['X', 'Y'].forEach(function (e) { $('foco' + e).value = 50; $('foco' + e + '-v').textContent = '50%'; });
        fundoPedido = null; logosVindas = null;
        preencher(vindo);
      });
    } else {
      recomecar.textContent = 'Limpar tudo';
      $('nota').textContent = 'Os textos ficam guardados neste navegador. As imagens que você abrir não ficam: ao recarregar a página, abra-as de novo.';
      recomecar.addEventListener('click', function () {
        if (!confirm('Limpar todos os campos e voltar ao início?')) return;
        try { localStorage.removeItem(CHAVE); } catch (e) {}
        lugar.removeChild(raiz);
        montar(lugar, op);
      });
    }

    // ---- Preenchimento a partir do item (modo automático)
    function preencher(v) {
      vindo = Object.assign({}, v || {});
      if ($('explica') && op.explica) { $('explica').textContent = op.explica; $('explica').hidden = false; }
      CAMPOS.forEach(function (k) {
        if (mem.manual[k]) return;
        var novo = vindo[k] == null ? '' : String(vindo[k]);
        if (estado[k] === novo) return;
        estado[k] = novo;
        $(k).value = novo;
        if (k === 'titulo') contar();
      });
      if (!mem.manual.fundo) fundoDoItem();
      if (!mem.manual.logos) logosDoItem();
      mostrarFundo(); desenharLogos();
      CAMPOS.forEach(marcar);
      agendar();
    }

    // ---- Início
    mostrarFundo(); desenharLogos();
    var carregando = carregarMotor().catch(function (e) {
      avisar('Não consegui carregar o motor do gerador (' + (e.message || e) + '). Atualize a página ou use um navegador mais recente.', 'gr-erro');
    });
    carregarLayouts().then(function (lista) {
      LAYOUTS = lista; porNome = {};
      LAYOUTS.forEach(function (L) { porNome[L.nome] = L; });
      if (!porNome[estado.layout]) estado.layout = LAYOUTS[0].nome;
      var sel = $('formato');
      sel.innerHTML = '';
      LAYOUTS.forEach(function (L) {
        var o = document.createElement('option'), t = tamanhoExportado(L, 1);
        o.value = L.nome; o.textContent = L.rotulo + ' · ' + t.largura + '×' + t.altura;
        sel.appendChild(o);
      });
      sel.value = estado.layout;
      desenharCamadas(); opcoesLinhas(); opcoesEscala();
      return carregando.then(function () { agendar(); });
    }).catch(function (e) {
      avisar('Não consegui carregar os formatos (' + e.message + ').', 'gr-erro');
    });

    return { raiz: raiz, preencher: preencher, agendar: agendar };
  }

  window.TCGerador = { montar: montar };
})();
