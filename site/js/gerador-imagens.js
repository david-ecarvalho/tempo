/* Tempo Continuum — Gerador de imagens.
   O desenho é feito pelo motor em Rust compilado para WebAssembly (js/motor/, fonte em motor-imagens/),
   direto no navegador de quem usa: nada é enviado ao site. Este arquivo cuida só da interface.
   Os formatos ficam em dados/layouts-imagens.json. */
(function () {
  'use strict';

  var CHAVE = 'tc-gerador-imagens';
  var MAX_LINHAS_OPCAO = 8;   // até quantas linhas o seletor oferece
  var LADO_MAX_FOTO = 4096;   // fotos maiores são reduzidas antes de ir para o motor
  var ALTURA_MIN_LOGO = 600;  // logos em SVG são rasterizadas pelo menos nesta altura
  var BASE = (document.currentScript && document.currentScript.src) || location.href;

  // =========================================================================
  // Motor (WebAssembly)
  // =========================================================================
  var motor = null;
  function carregarMotor() {
    return import(new URL('motor/motor_imagens.js', BASE).href).then(function (m) {
      return m.default().then(function () { motor = new m.Motor(); return motor; });
    });
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

  // =========================================================================
  // Montagem completa (feita pelo motor)
  // D = { titulo, linhasTitulo, selo, rodape: [..], link, fundo: nome|null, focoX, focoY, logos: [nomes] }
  // =========================================================================
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


  // =========================================================================
  // Interface da página
  // =========================================================================
  function iniciarInterface() {
    var raiz = document.getElementById('gerador');
    if (!raiz) return;
    var $ = function (id) { return document.getElementById(id); };
    var LAYOUTS = [], porNome = {};
    // Ficam só na memória do navegador. "nome" é como o motor conhece cada imagem.
    var imagens = { fundo: null, fundoNome: '', logos: [] }, proximaLogo = 0;
    var estado = {
      layout: 'post-retrato', titulo: 'Escreva aqui o título: ele se ajusta sozinho à área demarcada',
      selo: '', rodape1: '', rodape2: '', link: '', nome: '',
      focoX: 50, focoY: 50, escala: 1, guias: false, ajustes: {}, linhas: 0
    };
    try { Object.assign(estado, JSON.parse(localStorage.getItem(CHAVE) || '{}')); } catch (e) {}
    function guardar() { try { localStorage.setItem(CHAVE, JSON.stringify(estado)); } catch (e) {} }

    function dados() {
      return {
        titulo: estado.titulo, linhasTitulo: estado.linhas, selo: estado.selo, rodape: [estado.rodape1, estado.rodape2],
        link: estado.link, fundo: imagens.fundo ? 'fundo' : null, focoX: estado.focoX, focoY: estado.focoY,
        logos: imagens.logos.map(function (l) { return l.id; })
      };
    }
    function layoutAtual() { return aplicarAjustes(porNome[estado.layout], estado.ajustes); }

    // ---- Prévia
    var previa = $('gr-previa'), quadro = $('gr-quadro'), agendado = false;
    function agendar() {
      guardar();
      if (agendado) return;
      agendado = true;
      requestAnimationFrame(function () { agendado = false; desenharPrevia(); });
    }
    function desenharPrevia() {
      if (!LAYOUTS.length || !motor) return;
      var L = layoutAtual();
      var estreita = window.innerWidth < 860;
      var maxW = quadro.clientWidth - (estreita ? 0 : 40);
      var maxH = estreita ? Math.max(220, window.innerHeight * 0.42) : Math.max(320, Math.min(window.innerHeight * 0.75, 900));
      var disp = Math.min(maxW / L.largura, maxH / L.altura);
      previa.style.width = Math.floor(L.largura * disp) + 'px';
      previa.style.height = Math.floor(L.altura * disp) + 'px';
      var esc = Math.min(1, disp * (window.devicePixelRatio || 1));
      var rel = renderizar(previa, L, dados(), { escala: esc, guias: estado.guias });
      var ex = tamanhoExportado(L, 1);
      $('gr-medidas').textContent = 'Exporta em ' + ex.largura + ' × ' + ex.altura + ' px';
      relatorio(rel);
    }
    function relatorio(rel, extra) {
      var caixa = $('gr-relatorio');
      caixa.innerHTML = '';
      function add(t, cls) { var d = document.createElement('p'); d.textContent = t; if (cls) d.className = cls; caixa.appendChild(d); }
      if (rel && rel.titulo) add('Título em ' + Math.round(rel.titulo.fonte) + ' px, ' + rel.titulo.linhas + (rel.titulo.linhas === 1 ? ' linha' : ' linhas') + ' (máximo ' + rel.titulo.limite + ').');
      (rel && rel.avisos || []).forEach(function (a) { add('Atenção: ' + a + '.', 'gr-aviso'); });
      if (extra) add(extra.t, extra.cls);
    }
    window.addEventListener('resize', agendar);

    // ---- Campos de texto
    function ligar(id, chave) {
      var el = $(id);
      el.value = estado[chave] == null ? '' : estado[chave];
      el.addEventListener('input', function () { estado[chave] = el.value; if (id === 'gr-titulo') contar(); agendar(); });
    }
    function contar() { $('gr-contador').textContent = estado.titulo.length + ' caracteres'; }
    ligar('gr-titulo', 'titulo'); ligar('gr-selo', 'selo'); ligar('gr-rodape1', 'rodape1');
    ligar('gr-rodape2', 'rodape2'); ligar('gr-link', 'link'); ligar('gr-nome', 'nome');
    contar();

    $('gr-formato').addEventListener('change', function (ev) { estado.layout = ev.target.value; desenharCamadas(); opcoesLinhas(); opcoesEscala(); agendar(); });

    // ---- Número de linhas do título
    function opcoesLinhas() {
      var sel = $('gr-linhas'), L = porNome[estado.layout];
      sel.innerHTML = '';
      var auto = document.createElement('option');
      auto.value = '0';
      auto.textContent = 'Automático (até ' + L.titulo.max_linhas + ' neste formato)';
      sel.appendChild(auto);
      for (var n = 1; n <= MAX_LINHAS_OPCAO; n++) {
        var o = document.createElement('option');
        o.value = String(n);
        o.textContent = n === 1 ? '1 linha' : 'Até ' + n + ' linhas';
        sel.appendChild(o);
      }
      sel.value = String(estado.linhas || 0);
    }
    $('gr-linhas').addEventListener('change', function (ev) { estado.linhas = +ev.target.value; agendar(); });
    $('gr-guias').checked = !!estado.guias;
    $('gr-guias').addEventListener('change', function (ev) { estado.guias = ev.target.checked; agendar(); });
    // Tamanho do PNG baixado: o "exportar" do formato (se houver) vezes a resolução escolhida
    function tamanhoExportado(L, mult) {
      var base = L.exportar || { largura: L.largura, altura: L.altura };
      return { largura: Math.round(base.largura * mult), altura: Math.round(base.altura * mult), escala: base.largura / L.largura * mult };
    }
    function opcoesEscala() {
      var L = porNome[estado.layout], sel = $('gr-escala');
      [1, 2].forEach(function (m, i) {
        var t = tamanhoExportado(L, m);
        sel.options[i].textContent = (m === 1 ? 'Padrão' : '2× (mais nítida)') + ' · ' + t.largura + ' × ' + t.altura + ' px';
      });
    }
    $('gr-escala').value = String(estado.escala);
    $('gr-escala').addEventListener('change', function (ev) { estado.escala = +ev.target.value; guardar(); });

    // ---- Abrir imagens do computador
    function abrirImagem(arquivo) {
      return new Promise(function (ok, falha) {
        if (!motor) return falha(new Error('o gerador ainda está carregando; tente de novo em instantes'));
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
      $('gr-fundo-mini').hidden = !tem;
      $('gr-fundo-vazio').hidden = tem;
      if (tem) $('gr-fundo-mini').src = imagens.fundo.src;
      $('gr-fundo-nome').textContent = tem ? imagens.fundoNome : 'Clique ou arraste uma imagem';
      $('gr-remover-fundo').hidden = !tem;
    }
    function usarFundo(arq) {
      abrirImagem(arq).then(function (img) {
        enviarImagem('fundo', img, arq.type);
        imagens.fundo = img; imagens.fundoNome = arq.name; mostrarFundo(); agendar();
      }).catch(function (e) { relatorio(null, { t: e.message, cls: 'gr-erro' }); });
    }
    var zona = $('gr-zona-fundo');
    zona.addEventListener('click', function () { $('gr-arquivo-fundo').click(); });
    zona.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); $('gr-arquivo-fundo').click(); } });
    $('gr-arquivo-fundo').addEventListener('change', function (ev) { if (ev.target.files[0]) usarFundo(ev.target.files[0]); ev.target.value = ''; });
    ['dragenter', 'dragover'].forEach(function (t) { zona.addEventListener(t, function (ev) { ev.preventDefault(); zona.classList.add('gr-arrastando'); }); });
    ['dragleave', 'drop'].forEach(function (t) { zona.addEventListener(t, function (ev) { ev.preventDefault(); zona.classList.remove('gr-arrastando'); }); });
    zona.addEventListener('drop', function (ev) { if (ev.dataTransfer.files[0]) usarFundo(ev.dataTransfer.files[0]); });
    $('gr-remover-fundo').addEventListener('click', function () {
      imagens.fundo = null; if (motor) motor.remover_imagem('fundo'); mostrarFundo(); agendar();
    });
    ['X', 'Y'].forEach(function (eixo) {
      var el = $('gr-foco' + eixo), saida = $('gr-foco' + eixo + '-v');
      el.value = estado['foco' + eixo];
      saida.textContent = el.value + '%';
      el.addEventListener('input', function () { estado['foco' + eixo] = +el.value; saida.textContent = el.value + '%'; agendar(); });
    });

    // ---- Logos
    function desenharLogos() {
      var lista = $('gr-logos');
      lista.innerHTML = '';
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
            if (b[2] === 0) { motor.remover_imagem(L[i].id); L.splice(i, 1); }
            else if (j >= 0 && j < L.length) { var t = L[i]; L[i] = L[j]; L[j] = t; }
            desenharLogos(); agendar();
          });
          acoes.appendChild(bt);
        });
        item.appendChild(mini); item.appendChild(nome); item.appendChild(acoes);
        lista.appendChild(item);
      });
    }
    $('gr-adicionar-logo').addEventListener('click', function () { $('gr-arquivo-logo').click(); });
    $('gr-arquivo-logo').addEventListener('change', function (ev) {
      var arquivos = Array.prototype.slice.call(ev.target.files);
      ev.target.value = '';
      Promise.all(arquivos.map(function (a) {
        return abrirImagem(a).then(function (img) {
          var id = 'logo-' + (proximaLogo++);
          enviarImagem(id, img, a.type);
          return { img: img, nome: a.name, id: id };
        });
      })).then(function (novas) { imagens.logos = imagens.logos.concat(novas); desenharLogos(); agendar(); })
        .catch(function (e) { relatorio(null, { t: e.message, cls: 'gr-erro' }); });
    });

    // ---- Camadas
    var TIPOS = { cor: 'Cor', gradiente: 'Gradiente' };
    function desenharCamadas() {
      var L = porNome[estado.layout], aj = estado.ajustes[L.nome] || (estado.ajustes[L.nome] = {});
      var lista = $('gr-camadas');
      lista.innerHTML = '';
      L.camadas.forEach(function (c, i) {
        var a = aj[i] || {}, visivel = a.visivel !== false;
        var item = document.createElement('div');
        item.className = 'gr-camada' + (visivel ? '' : ' gr-oculta');
        var topo = document.createElement('label');
        topo.className = 'gr-camada-topo';
        var marca = document.createElement('input'); marca.type = 'checkbox'; marca.checked = visivel;
        var amostra = document.createElement('span'); amostra.className = 'gr-amostra';
        amostra.style.background = c.tipo === 'gradiente' ? 'linear-gradient(' + c.cor + ',' + (c.cor2 || c.cor) + ')' : c.cor;
        var nome = document.createElement('span');
        nome.textContent = (i + 1) + '. ' + (TIPOS[c.tipo] || c.tipo) + ' · ' + c.largura + '×' + c.altura + (c.desfoque ? ' · vidro' : '');
        topo.appendChild(marca); topo.appendChild(amostra); topo.appendChild(nome);
        item.appendChild(topo);
        marca.addEventListener('change', function () {
          aj[i] = aj[i] || {};
          if (marca.checked) delete aj[i].visivel; else aj[i].visivel = false;
          item.classList.toggle('gr-oculta', !marca.checked);
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
    $('gr-restaurar').addEventListener('click', function () { estado.ajustes[estado.layout] = {}; desenharCamadas(); agendar(); });

    // ---- Baixar
    function nomeArquivo(L) {
      var base = (estado.nome || estado.titulo || 'imagem').normalize('NFD').replace(/[̀-ͯ]/g, '')
        .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'imagem';
      var t = tamanhoExportado(L, estado.escala);
      return base + '-' + L.nome + '-' + t.largura + 'x' + t.altura + '.png';
    }
    function baixar(nomeLayout) {
      if (!motor) return Promise.reject(new Error('o gerador ainda está carregando'));
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
    $('gr-baixar').addEventListener('click', function () {
      baixar(estado.layout).then(function (r) { relatorio(r.rel, { t: 'Baixado: ' + r.nome, cls: 'gr-ok' }); },
        function (e) { relatorio(null, { t: e.message, cls: 'gr-erro' }); });
    });
    $('gr-baixar-todos').addEventListener('click', function () {
      var nomes = [], cadeia = Promise.resolve();
      LAYOUTS.forEach(function (L) {
        cadeia = cadeia.then(function () { return baixar(L.nome); })
          .then(function (r) { nomes.push(r.nome); return new Promise(function (ok) { setTimeout(ok, 350); }); });
      });
      cadeia.then(function () { relatorio(null, { t: 'Baixados: ' + nomes.join(', '), cls: 'gr-ok' }); },
        function (e) { relatorio(null, { t: e.message, cls: 'gr-erro' }); });
    });
    $('gr-recomecar').addEventListener('click', function () {
      if (!confirm('Limpar todos os campos e voltar ao início?')) return;
      try { localStorage.removeItem(CHAVE); } catch (e) {}
      location.reload();
    });

    // ---- Início: carrega o motor e os formatos ao mesmo tempo
    var carregando = carregarMotor().catch(function (e) {
      relatorio(null, { t: 'Não consegui carregar o motor do gerador (' + (e.message || e) + '). Atualize a página ou use um navegador mais recente.', cls: 'gr-erro' });
    });
    fetch('dados/layouts-imagens.json').then(function (r) { return r.json(); }).then(function (j) {
      LAYOUTS = j.layouts;
      LAYOUTS.forEach(function (L) { porNome[L.nome] = L; });
      if (!porNome[estado.layout]) estado.layout = LAYOUTS[0].nome;
      $('gr-formato').innerHTML = '';
      LAYOUTS.forEach(function (L) {
        var o = document.createElement('option');
        var t = tamanhoExportado(L, 1);
        o.value = L.nome; o.textContent = L.rotulo + ' · ' + t.largura + '×' + t.altura;
        $('gr-formato').appendChild(o);
      });
      $('gr-formato').value = estado.layout;
      mostrarFundo(); desenharLogos(); desenharCamadas(); opcoesLinhas(); opcoesEscala();
      return carregando.then(function () { agendar(); });
    }).catch(function (e) {
      relatorio(null, { t: 'Não consegui carregar os formatos (' + e.message + ').', cls: 'gr-erro' });
    });

    window.__gerador = { agendar: agendar };
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciarInterface);
  else iniciarInterface();
})();
