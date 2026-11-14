//! Tempo Continuum — motor do Gerador de imagens, em Rust compilado para WebAssembly.
//! Recebe o formato (dados/layouts-imagens.json) e o que a pessoa preencheu, e devolve os
//! pixels da imagem pronta. Tudo roda no navegador de quem usa: nada é enviado ao site.

mod desenho;
mod layout;
mod texto;

use desenho::{cor, Imagem};
use layout::{Dados, Layout};
use std::collections::HashMap;
use texto::{Ajuste, Area, Fonte, Opcoes};
use tiny_skia::{BlendMode, Color, Paint, Pixmap, Rect, Shader, Stroke, StrokeDash, Transform};
use wasm_bindgen::prelude::*;

/// Menor fonte permitida quando a pessoa fixa o número de linhas do título
const PISO_FONTE: f32 = 16.0;
/// Maior lado aceito para a imagem final, para não estourar a memória do navegador
const LADO_MAXIMO: f32 = 8192.0;

#[wasm_bindgen]
pub struct Motor {
    fonte: Fonte,
    imagens: HashMap<String, Imagem>,
}

#[wasm_bindgen]
pub struct Resultado {
    largura: u32,
    altura: u32,
    pixels: Vec<u8>,
    relatorio: String,
}

#[wasm_bindgen]
impl Resultado {
    #[wasm_bindgen(getter)]
    pub fn largura(&self) -> u32 {
        self.largura
    }
    #[wasm_bindgen(getter)]
    pub fn altura(&self) -> u32 {
        self.altura
    }
    /// RGBA sem pré-multiplicação, pronto para ImageData
    #[wasm_bindgen(getter)]
    pub fn pixels(&self) -> Vec<u8> {
        self.pixels.clone()
    }
    /// JSON: { titulo?: {fonte, linhas, cortado, limite}, avisos: [..] }
    #[wasm_bindgen(getter)]
    pub fn relatorio(&self) -> String {
        self.relatorio.clone()
    }
}

#[wasm_bindgen]
impl Motor {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Motor {
        Motor { fonte: Fonte::nova(), imagens: HashMap::new() }
    }

    /// Guarda uma imagem (fundo ou logo) para usar nas próximas renderizações
    pub fn definir_imagem(&mut self, nome: &str, largura: u32, altura: u32, rgba: &[u8]) -> Result<(), JsError> {
        let img = Imagem::nova(largura, altura, rgba).ok_or_else(|| JsError::new("imagem inválida"))?;
        self.imagens.insert(nome.to_string(), img);
        Ok(())
    }

    pub fn remover_imagem(&mut self, nome: &str) {
        self.imagens.remove(nome);
    }

    /// Monta a imagem. `escala` multiplica as medidas do formato; `guias` mostra as áreas.
    pub fn renderizar(&self, layout_json: &str, dados_json: &str, escala: f32, guias: bool) -> Result<Resultado, JsError> {
        let l: Layout = serde_json::from_str(layout_json).map_err(|e| JsError::new(&format!("formato inválido: {e}")))?;
        let d: Dados = serde_json::from_str(dados_json).map_err(|e| JsError::new(&format!("dados inválidos: {e}")))?;
        let e = escala.min(LADO_MAXIMO / l.largura.max(l.altura)).max(0.01);
        let (w, h) = ((l.largura * e).round() as u32, (l.altura * e).round() as u32);
        let mut pm = Pixmap::new(w.max(1), h.max(1)).ok_or_else(|| JsError::new("imagem grande demais"))?;
        let mut rel = Relatorio::default();
        self.montar(&mut pm, &l, &d, e, &mut rel);
        if guias {
            self.desenhar_guias(&mut pm, &l, Transform::from_scale(e, e));
        }
        let mut pixels = pm.take();
        for px in pixels.chunks_exact_mut(4) {
            let a = px[3] as u32;
            if a > 0 && a < 255 {
                for c in &mut px[..3] {
                    *c = ((*c as u32 * 255 + a / 2) / a).min(255) as u8;
                }
            }
        }
        Ok(Resultado { largura: w.max(1), altura: h.max(1), pixels, relatorio: rel.json() })
    }
}

impl Default for Motor {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Default)]
struct Relatorio {
    titulo: Option<(f32, usize, bool, u32)>,
    avisos: Vec<String>,
}

impl Relatorio {
    fn json(&self) -> String {
        let mut v = serde_json::json!({ "avisos": self.avisos });
        if let Some((fonte, linhas, cortado, limite)) = self.titulo {
            v["titulo"] = serde_json::json!({ "fonte": fonte, "linhas": linhas, "cortado": cortado, "limite": limite });
        }
        v.to_string()
    }
}

fn plural_linhas(n: u32) -> String {
    if n == 1 { "1 linha".into() } else { format!("{n} linhas") }
}

impl Motor {
    fn montar(&self, pm: &mut Pixmap, l: &Layout, d: &Dados, e: f32, rel: &mut Relatorio) {
        let t = Transform::from_scale(e, e);

        // 1. Fundo
        pm.fill(cor(l.cor_fundo.as_deref().unwrap_or("#000"), 1.0));
        if let Some(img) = d.fundo.as_deref().and_then(|n| self.imagens.get(n)) {
            let s = (l.largura / img.largura()).max(l.altura / img.altura());
            let (dw, dh) = (img.largura() * s, img.altura() * s);
            let x = (l.largura - dw) * (d.foco_x / 100.0);
            let y = (l.altura - dh) * (d.foco_y / 100.0);
            img.desenhar(pm, x, y, dw, dh, t);
        }

        // 2. Camadas com transparência
        for c in &l.camadas {
            let raio = c.raio.unwrap_or(0.0);
            if let Some(sigma) = c.desfoque.filter(|s| *s > 0.0) {
                if let Some(px) = desenho::retangulo(c.x * e, c.y * e, c.largura * e, c.altura * e, raio * e) {
                    desenho::desfocar_regiao(pm, &px, sigma * e);
                }
            }
            let c1 = cor(c.cor.as_deref().unwrap_or("#000"), c.alpha.unwrap_or(1.0));
            let gradiente = c.tipo == "gradiente";
            let angulo = if !gradiente {
                180.0
            } else {
                match &c.direcao {
                    Some(serde_json::Value::Number(n)) => n.as_f64().unwrap_or(180.0) as f32,
                    Some(serde_json::Value::String(s)) => match s.as_str() {
                        "para cima" => 0.0,
                        "para direita" => 90.0,
                        "para esquerda" => 270.0,
                        _ => 180.0,
                    },
                    _ => 180.0,
                }
            };
            let c2 = if gradiente {
                cor(c.cor2.as_deref().or(c.cor.as_deref()).unwrap_or("#000"), c.alpha2.unwrap_or(0.0))
            } else {
                c1
            };
            let mistura = desenho::modo_mistura(c.mistura.as_deref());
            if raio <= 0.0 && mistura == BlendMode::SourceOver {
                // Caso comum (todas as camadas atuais): retângulo reto, mistura normal
                let (x, y, w, h) = (c.x * e, c.y * e, c.largura * e, c.altura * e);
                let (a, b, k) = if gradiente { desenho::coef_gradiente(x, y, w, h, angulo) } else { (0.0, 0.0, 0.0) };
                desenho::preencher_faixa(pm, &desenho::Faixa { x0: x, y0: y, x1: x + w, y1: y + h, a, b, c: k }, c1, c2);
            } else if let Some(caminho) = desenho::retangulo(c.x, c.y, c.largura, c.altura, raio) {
                let shader = if gradiente {
                    desenho::gradiente(c.x, c.y, c.largura, c.altura, angulo, c1, c2)
                } else {
                    Shader::SolidColor(c1)
                };
                desenho::preencher(pm, &caminho, shader, mistura, t, None);
            }
        }

        // 3. Selo, logos e QR
        if let (Some(s), texto) = (&l.selo, d.selo.trim()) {
            if !texto.is_empty() {
                self.desenhar_selo(pm, s, texto, t);
            }
        }
        if let Some(a) = &l.logos {
            let imgs: Vec<&Imagem> = d.logos.iter().filter_map(|n| self.imagens.get(n)).collect();
            if !imgs.is_empty() {
                desenhar_logos(pm, a, &imgs, t);
            }
        }
        if let (Some(q), link) = (&l.qr, d.link.trim()) {
            if !link.is_empty() && !desenhar_qr(pm, q, link, e) {
                rel.avisos.push("o link é longo demais para o QR code".into());
            }
        }

        // 4. Título e rodapé
        if let (Some(a), titulo) = (&l.titulo, d.titulo.trim()) {
            if !titulo.is_empty() {
                let escolhidas = d.linhas_titulo;
                let minimo = if escolhidas > 0 { a.fonte_min.min(PISO_FONTE) } else { a.fonte_min };
                let limite = if escolhidas > 0 { Some(escolhidas) } else { a.max_linhas };
                let r = texto::ajustar(
                    &self.fonte,
                    &[titulo.to_string()],
                    &Area { largura: a.largura, altura: a.altura },
                    &Opcoes {
                        max: a.fonte_max,
                        min: minimo,
                        entrelinha: a.entrelinha.unwrap_or(1.1),
                        max_linhas: limite.map(|n| n as usize),
                        balancear: true,
                    },
                );
                let bloco = Bloco { x: a.x, y: a.y, largura: a.largura, altura: a.altura, alinhar: a.alinhar.as_deref(), vertical: a.vertical.as_deref() };
                self.desenhar_bloco(pm, &r, &bloco, &[cor(&a.cor, 1.0)], t);
                rel.titulo = Some((r.fonte, r.linhas.len(), r.cortado, limite.unwrap_or(0)));
                if r.cortado {
                    rel.avisos.push(if escolhidas > 0 {
                        format!("o título não coube em {} nem com a menor fonte; o final foi cortado com \"…\"", plural_linhas(escolhidas))
                    } else {
                        "o título não coube nem no tamanho mínimo; o final foi cortado com \"…\"".into()
                    });
                } else if r.fonte < a.fonte_min {
                    rel.avisos.push(format!(
                        "para caber em {}, a fonte ficou menor que o recomendado para este formato ({} px)",
                        plural_linhas(escolhidas),
                        a.fonte_min
                    ));
                } else if r.quebrou_palavra {
                    rel.avisos.push("uma palavra do título é longa demais e foi quebrada".into());
                }
            }
        }
        let rod: Vec<String> = d.rodape.iter().map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect();
        if let Some(a) = &l.rodape {
            if !rod.is_empty() {
                let r = texto::ajustar(
                    &self.fonte,
                    &rod,
                    &Area { largura: a.largura, altura: a.altura },
                    &Opcoes { max: a.fonte, min: (a.fonte * 0.6).round(), entrelinha: a.entrelinha.unwrap_or(1.1), max_linhas: None, balancear: false },
                );
                let cores: Vec<Color> = (0..rod.len())
                    .map(|i| match (&a.cor_destaque, i) {
                        (Some(dest), 0) => cor(dest, 1.0),
                        _ => cor(&a.cor, 1.0),
                    })
                    .collect();
                let bloco = Bloco { x: a.x, y: a.y, largura: a.largura, altura: a.altura, alinhar: a.alinhar.as_deref(), vertical: a.vertical.as_deref() };
                self.desenhar_bloco(pm, &r, &bloco, &cores, t);
                if r.cortado {
                    rel.avisos.push("o rodapé não coube; o final foi cortado".into());
                }
            }
        }
    }

    fn desenhar_bloco(&self, pm: &mut Pixmap, r: &Ajuste, a: &Bloco, cores: &[Color], t: Transform) {
        let f = &self.fonte;
        let (asc, desc) = (f.em_px(f.asc, r.fonte), f.em_px(f.desc, r.fonte));
        let altura_linha = r.fonte * r.entrelinha;
        let total = r.linhas.len() as f32 * altura_linha;
        let y0 = match a.vertical {
            Some("base") => a.y + a.altura - total,
            Some("centro") => a.y + (a.altura - total) / 2.0,
            _ => a.y,
        };
        for (i, l) in r.linhas.iter().enumerate() {
            let w = f.medir(&l.t, r.fonte);
            let x = match a.alinhar {
                Some("centro") => a.x + (a.largura - w) / 2.0,
                Some("direita") => a.x + a.largura - w,
                _ => a.x,
            };
            let base = y0 + i as f32 * altura_linha + altura_linha / 2.0 + (asc - desc) / 2.0;
            let c = cores.get(l.p).or(cores.first()).copied().unwrap_or(Color::WHITE);
            f.desenhar(pm, &l.t, x, base, r.fonte, c, t);
        }
    }

    fn desenhar_selo(&self, pm: &mut Pixmap, s: &layout::Selo, texto: &str, t: Transform) {
        let f = &self.fonte;
        let texto = texto.to_uppercase();
        let letras: Vec<String> = texto.chars().map(|c| c.to_string()).collect();
        let larguras: Vec<f32> = letras.iter().map(|c| f.medir(c, s.fonte)).collect();
        let w: f32 = larguras.iter().sum::<f32>() + s.espaco_letras * letras.len().saturating_sub(1) as f32;
        if let Some(r) = Rect::from_xywh(s.x, s.y, w + 2.0 * s.margem, s.altura) {
            let mut p = Paint::default();
            p.set_color(cor(&s.cor_fundo, s.alpha_fundo.unwrap_or(1.0)));
            p.anti_alias = true;
            pm.fill_rect(r, &p, t, None);
        }
        let capa = f.em_px(f.capa, s.fonte);
        let mut x = s.x + s.margem;
        let base = s.y + s.altura / 2.0 + capa / 2.0;
        for (ch, lw) in letras.iter().zip(&larguras) {
            f.desenhar(pm, ch, x, base, s.fonte, cor(&s.cor, 1.0), t);
            x += lw + s.espaco_letras;
        }
    }

    fn desenhar_guias(&self, pm: &mut Pixmap, l: &Layout, t: Transform) {
        let mut areas: Vec<(&str, f32, f32, f32, f32)> = Vec::new();
        if let Some(a) = &l.titulo { areas.push(("titulo", a.x, a.y, a.largura, a.altura)); }
        if let Some(a) = &l.rodape { areas.push(("rodape", a.x, a.y, a.largura, a.altura)); }
        if let Some(a) = &l.logos { areas.push(("logos", a.x, a.y, a.largura, a.altura)); }
        if let Some(q) = &l.qr { areas.push(("qr", q.x, q.y, q.tamanho, q.tamanho)); }
        let esc = l.largura / 1080.0;
        let rosa = cor("#ff2bd6", 1.0);
        for (nome, x, y, w, h) in areas {
            let mut p = Paint::default();
            p.anti_alias = true;
            p.set_color(Color::from_rgba8(255, 43, 214, 20));
            if let Some(r) = Rect::from_xywh(x, y, w, h) {
                pm.fill_rect(r, &p, t, None);
            }
            p.set_color(rosa);
            if let Some(caminho) = desenho::retangulo(x + 1.0, y + 1.0, w - 2.0, h - 2.0, 0.0) {
                let stroke = Stroke { width: 2.0 * esc, dash: StrokeDash::new(vec![10.0 * esc, 6.0 * esc], 0.0), ..Stroke::default() };
                pm.stroke_path(&caminho, &p, &stroke, t, None);
            }
            let fs = 16.0 * esc;
            let lw = self.fonte.medir(nome, fs) + 12.0 * esc;
            if let Some(r) = Rect::from_xywh(x, y - 24.0 * esc, lw, 22.0 * esc) {
                pm.fill_rect(r, &p, t, None);
            }
            let base = y - 13.0 * esc + self.fonte.em_px(self.fonte.capa, fs) / 2.0;
            self.fonte.desenhar(pm, nome, x + 6.0 * esc, base, fs, Color::WHITE, t);
        }
    }
}

struct Bloco<'a> {
    x: f32,
    y: f32,
    largura: f32,
    altura: f32,
    alinhar: Option<&'a str>,
    vertical: Option<&'a str>,
}

fn desenhar_logos(pm: &mut Pixmap, a: &layout::AreaLogos, imgs: &[&Imagem], t: Transform) {
    let prop: Vec<f32> = imgs.iter().map(|i| if i.altura() > 0.0 { i.largura() / i.altura() } else { 3.0 }).collect();
    let gaps = (imgs.len() as f32 - 1.0) * a.espaco;
    let mut h = a.altura;
    let soma: f32 = prop.iter().map(|p| p * h).sum();
    if soma + gaps > a.largura {
        h = h * (a.largura - gaps) / soma;
    }
    let total: f32 = prop.iter().map(|p| p * h).sum::<f32>() + gaps;
    let mut x = match a.alinhar.as_deref() {
        Some("direita") => a.x + a.largura - total,
        Some("centro") => a.x + (a.largura - total) / 2.0,
        _ => a.x,
    };
    let y = a.y + (a.altura - h) / 2.0;
    for (img, p) in imgs.iter().zip(&prop) {
        img.desenhar(pm, x, y, p * h, h, t);
        x += p * h + a.espaco;
    }
}

/// Desenha o QR code; devolve false se o link não cabe num QR
fn desenhar_qr(pm: &mut Pixmap, q: &layout::Qr, texto: &str, e: f32) -> bool {
    let Ok(codigo) = qrcode::QrCode::with_error_correction_level(texto.as_bytes(), qrcode::EcLevel::M) else {
        return false;
    };
    let n = codigo.width();
    let t = Transform::from_scale(e, e);
    if let Some(fundo) = desenho::retangulo(q.x, q.y, q.tamanho, q.tamanho, q.raio.unwrap_or(0.0)) {
        let c = cor(&q.cor_fundo, q.alpha_fundo.unwrap_or(1.0));
        desenho::preencher(pm, &fundo, Shader::SolidColor(c), BlendMode::SourceOver, t, None);
    }
    // Módulos em pixels inteiros do arquivo final, para ficarem nítidos
    let mut p = Paint::default();
    p.set_color(cor(&q.cor, 1.0));
    p.anti_alias = false;
    let (x0, y0, lado) = ((q.x + q.margem) * e, (q.y + q.margem) * e, (q.tamanho - 2.0 * q.margem) * e);
    let pos = |i: usize, base: f32| (base + i as f32 * lado / n as f32).round();
    for r in 0..n {
        for c in 0..n {
            if codigo[(c, r)] == qrcode::Color::Dark {
                let (xa, ya) = (pos(c, x0), pos(r, y0));
                if let Some(rect) = Rect::from_xywh(xa, ya, pos(c + 1, x0) - xa, pos(r + 1, y0) - ya) {
                    pm.fill_rect(rect, &p, Transform::identity(), None);
                }
            }
        }
    }
    true
}
