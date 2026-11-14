//! Fonte Montserrat embutida, medição de texto, quebra de linhas e ajuste do texto à área.
//! Sem hinting, a largura de um texto é proporcional ao tamanho da fonte: mede-se uma vez em
//! unidades da fonte (com kerning e ligaduras, via rustybuzz) e guarda-se o resultado.
use rustybuzz::ttf_parser::{self, OutlineBuilder};
use std::cell::RefCell;
use std::collections::HashMap;
use tiny_skia::{Color, FillRule, Paint, PathBuilder, Pixmap, Transform};

static FONTE: &[u8] = include_bytes!("../fonte/Montserrat-Medium.ttf");

pub struct Fonte {
    shaper: rustybuzz::Face<'static>,
    face: ttf_parser::Face<'static>,
    upem: f32,
    /// fontBoundingBoxAscent/Descent do canvas, em unidades da fonte
    pub asc: f32,
    pub desc: f32,
    /// altura das maiúsculas (actualBoundingBoxAscent de "H"), em unidades
    pub capa: f32,
    larguras: RefCell<HashMap<String, f32>>,
}

impl Fonte {
    pub fn nova() -> Fonte {
        let face = ttf_parser::Face::parse(FONTE, 0).expect("fonte embutida inválida");
        let shaper = rustybuzz::Face::from_slice(FONTE, 0).expect("fonte embutida inválida");
        let upem = face.units_per_em() as f32;
        let asc = face.ascender() as f32;
        let desc = -(face.descender() as f32);
        let capa = face
            .glyph_index('H')
            .and_then(|g| face.glyph_bounding_box(g))
            .map(|b| b.y_max as f32)
            .unwrap_or(upem * 0.7);
        Fonte { shaper, face, upem, asc, desc, capa, larguras: RefCell::new(HashMap::new()) }
    }

    fn moldar(&self, texto: &str) -> rustybuzz::GlyphBuffer {
        let mut buf = rustybuzz::UnicodeBuffer::new();
        buf.push_str(texto);
        rustybuzz::shape(&self.shaper, &[], buf)
    }

    /// Largura do texto em pixels, no tamanho `fs`
    pub fn medir(&self, texto: &str, fs: f32) -> f32 {
        if texto.is_empty() {
            return 0.0;
        }
        if let Some(u) = self.larguras.borrow().get(texto) {
            return u * fs / self.upem;
        }
        let g = self.moldar(texto);
        let u: f32 = g.glyph_positions().iter().map(|p| p.x_advance as f32).sum();
        let mut cache = self.larguras.borrow_mut();
        if cache.len() > 20_000 {
            cache.clear();
        }
        cache.insert(texto.to_string(), u);
        u * fs / self.upem
    }

    /// Desenha o texto com a linha de base em (x, y), coordenadas do formato; `t` leva ao pixel final
    pub fn desenhar(&self, pm: &mut Pixmap, texto: &str, x: f32, y: f32, fs: f32, cor: Color, t: Transform) {
        let g = self.moldar(texto);
        let s = fs / self.upem;
        let mut pb = PathBuilder::new();
        let mut cx = x;
        for (info, pos) in g.glyph_infos().iter().zip(g.glyph_positions()) {
            let mut c = Contorno {
                pb: &mut pb,
                ox: cx + pos.x_offset as f32 * s,
                oy: y - pos.y_offset as f32 * s,
                s,
            };
            self.face.outline_glyph(ttf_parser::GlyphId(info.glyph_id as u16), &mut c);
            cx += pos.x_advance as f32 * s;
        }
        if let Some(caminho) = pb.finish() {
            let mut paint = Paint::default();
            paint.set_color(cor);
            paint.anti_alias = true;
            pm.fill_path(&caminho, &paint, FillRule::Winding, t, None);
        }
    }

    pub fn em_px(&self, unidades: f32, fs: f32) -> f32 {
        unidades * fs / self.upem
    }
}

struct Contorno<'a> {
    pb: &'a mut PathBuilder,
    ox: f32,
    oy: f32,
    s: f32,
}

impl Contorno<'_> {
    fn p(&self, x: f32, y: f32) -> (f32, f32) {
        (self.ox + x * self.s, self.oy - y * self.s)
    }
}

impl OutlineBuilder for Contorno<'_> {
    fn move_to(&mut self, x: f32, y: f32) {
        let (a, b) = self.p(x, y);
        self.pb.move_to(a, b);
    }
    fn line_to(&mut self, x: f32, y: f32) {
        let (a, b) = self.p(x, y);
        self.pb.line_to(a, b);
    }
    fn quad_to(&mut self, x1: f32, y1: f32, x: f32, y: f32) {
        let (a, b) = self.p(x1, y1);
        let (c, d) = self.p(x, y);
        self.pb.quad_to(a, b, c, d);
    }
    fn curve_to(&mut self, x1: f32, y1: f32, x2: f32, y2: f32, x: f32, y: f32) {
        let (a, b) = self.p(x1, y1);
        let (c, d) = self.p(x2, y2);
        let (e, f) = self.p(x, y);
        self.pb.cubic_to(a, b, c, d, e, f);
    }
    fn close(&mut self) {
        self.pb.close();
    }
}

// ===========================================================================
// Quebra de linhas e ajuste à área
// ===========================================================================

#[derive(Clone)]
pub struct Linha {
    pub t: String,
    /// índice do parágrafo (define a cor no rodapé)
    pub p: usize,
}

pub struct Ajuste {
    pub fonte: f32,
    pub linhas: Vec<Linha>,
    pub cortado: bool,
    pub quebrou_palavra: bool,
    pub entrelinha: f32,
}

pub struct Opcoes {
    pub max: f32,
    pub min: f32,
    pub entrelinha: f32,
    pub max_linhas: Option<usize>,
    pub balancear: bool,
}

pub struct Area {
    pub largura: f32,
    pub altura: f32,
}

/// Quebra por palavras; None se alguma palavra não cabe sozinha na largura
fn quebrar(f: &Fonte, fs: f32, texto: &str, largura: f32) -> Option<Vec<String>> {
    let mut linhas = Vec::new();
    let mut atual = String::new();
    for p in texto.split_whitespace() {
        if f.medir(p, fs) > largura + 0.5 {
            return None;
        }
        if atual.is_empty() {
            atual = p.to_string();
            continue;
        }
        let tentativa = format!("{atual} {p}");
        if f.medir(&tentativa, fs) <= largura + 0.5 {
            atual = tentativa;
        } else {
            linhas.push(std::mem::replace(&mut atual, p.to_string()));
        }
    }
    if !atual.is_empty() {
        linhas.push(atual);
    }
    Some(linhas)
}

/// Quebra forçada: corta palavras longas onde precisar
fn quebrar_forcado(f: &Fonte, fs: f32, texto: &str, largura: f32) -> Vec<String> {
    let mut pedacos: Vec<String> = Vec::new();
    for palavra in texto.split_whitespace() {
        let mut p: Vec<char> = palavra.chars().collect();
        while p.len() > 1 && f.medir(&p.iter().collect::<String>(), fs) > largura {
            let mut n = p.len() - 1;
            while n > 1 && f.medir(&p[..n].iter().collect::<String>(), fs) > largura {
                n -= 1;
            }
            pedacos.push(p[..n].iter().collect());
            p = p[n..].to_vec();
        }
        pedacos.push(p.into_iter().collect());
    }
    quebrar(f, fs, &pedacos.join(" "), largura).unwrap_or(pedacos)
}

pub fn ajustar(f: &Fonte, paragrafos: &[String], a: &Area, op: &Opcoes) -> Ajuste {
    let (w, h, lh) = (a.largura, a.altura, op.entrelinha);
    let max_l = op.max_linhas.unwrap_or(usize::MAX);
    let tentar = |fs: f32| -> Option<Vec<Linha>> {
        let mut linhas = Vec::new();
        for (i, par) in paragrafos.iter().enumerate() {
            for t in quebrar(f, fs, par, w)? {
                linhas.push(Linha { t, p: i });
            }
        }
        if linhas.len() as f32 * fs * lh > h + 0.5 || linhas.len() > max_l {
            return None;
        }
        Some(linhas)
    };

    let (mut lo, mut hi) = (op.min, op.max);
    let mut melhor: Option<f32> = None;
    if tentar(hi).is_some() {
        melhor = Some(hi);
    } else {
        while hi - lo > 0.25 {
            let meio = (lo + hi) / 2.0;
            if tentar(meio).is_some() {
                melhor = Some(meio);
                lo = meio;
            } else {
                hi = meio;
            }
        }
        if melhor.is_none() && tentar(op.min).is_some() {
            melhor = Some(op.min);
        }
    }

    if let Some(m) = melhor {
        let m = (m * 4.0).floor() / 4.0;
        let mut linhas = tentar(m).or_else(|| tentar(op.min)).unwrap_or_default();
        // Equilibra as linhas (como text-wrap: balance): menor largura com o mesmo nº de linhas
        if op.balancear && paragrafos.len() == 1 && linhas.len() > 1 {
            let n = linhas.len();
            let (mut a0, mut a1) = (w * 0.4, w);
            while a1 - a0 > 1.0 {
                let meio = (a0 + a1) / 2.0;
                match quebrar(f, m, &paragrafos[0], meio) {
                    Some(l) if l.len() <= n => a1 = meio,
                    _ => a0 = meio,
                }
            }
            if let Some(eq) = quebrar(f, m, &paragrafos[0], a1) {
                if eq.len() == n {
                    linhas = eq.into_iter().map(|t| Linha { t, p: 0 }).collect();
                }
            }
        }
        return Ajuste { fonte: m, linhas, cortado: false, quebrou_palavra: false, entrelinha: lh };
    }

    // Não coube nem no mínimo: quebra palavras e corta o final com "…"
    let fs = op.min;
    let limite = ((h / (fs * lh)).floor() as usize).min(max_l).max(1);
    let mut todas: Vec<Linha> = Vec::new();
    for (i, par) in paragrafos.iter().enumerate() {
        for t in quebrar_forcado(f, fs, par, w) {
            todas.push(Linha { t, p: i });
        }
    }
    let cortado = todas.len() > limite;
    if cortado {
        todas.truncate(limite);
        let ult = &mut todas[limite - 1];
        let mut pal: Vec<&str> = ult.t.split(' ').collect();
        while pal.len() > 1 && f.medir(&format!("{}…", pal.join(" ")), fs) > w {
            pal.pop();
        }
        let base = pal.join(" ");
        let base = base.trim_end_matches(|c: char| c.is_whitespace() || ",.;:–—-".contains(c));
        ult.t = format!("{base}…");
    }
    Ajuste { fonte: fs, linhas: todas, cortado, quebrou_palavra: true, entrelinha: lh }
}
