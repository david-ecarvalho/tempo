//! Utilidades de desenho: cores, retângulos arredondados, gradientes, desfoque e imagens.
use tiny_skia::{
    BlendMode, Color, FillRule, FilterQuality, GradientStop, IntSize, LinearGradient, Mask, Paint,
    Path, PathBuilder, Pattern, Pixmap, PixmapPaint, Point, Rect, Shader, SpreadMode, Transform,
};

/// "#rgb" ou "#rrggbb" com opacidade
pub fn cor(hex: &str, alpha: f32) -> Color {
    let h = hex.trim().trim_start_matches('#');
    let h: String = if h.len() == 3 { h.chars().flat_map(|c| [c, c]).collect() } else { h.to_string() };
    let n = u32::from_str_radix(h.get(..6).unwrap_or("000000"), 16).unwrap_or(0);
    Color::from_rgba8((n >> 16) as u8, (n >> 8) as u8, n as u8, (alpha.clamp(0.0, 1.0) * 255.0).round() as u8)
}

/// Retângulo com cantos arredondados (como arcTo do canvas)
pub fn retangulo(x: f32, y: f32, w: f32, h: f32, r: f32) -> Option<Path> {
    let r = r.min(w / 2.0).min(h / 2.0).max(0.0);
    if r <= 0.0 {
        return Rect::from_xywh(x, y, w, h).map(PathBuilder::from_rect);
    }
    let k = r * 0.552_284_8; // aproximação de quarto de círculo por cúbica
    let mut pb = PathBuilder::new();
    pb.move_to(x + r, y);
    pb.line_to(x + w - r, y);
    pb.cubic_to(x + w - r + k, y, x + w, y + r - k, x + w, y + r);
    pb.line_to(x + w, y + h - r);
    pb.cubic_to(x + w, y + h - r + k, x + w - r + k, y + h, x + w - r, y + h);
    pb.line_to(x + r, y + h);
    pb.cubic_to(x + r - k, y + h, x, y + h - r + k, x, y + h - r);
    pb.line_to(x, y + r);
    pb.cubic_to(x, y + r - k, x + r - k, y, x + r, y);
    pb.close();
    pb.finish()
}

pub fn preencher(pm: &mut Pixmap, caminho: &Path, shader: Shader, mistura: BlendMode, t: Transform, mask: Option<&Mask>) {
    let paint = Paint { shader, blend_mode: mistura, anti_alias: true, ..Paint::default() };
    pm.fill_path(caminho, &paint, FillRule::Winding, t, mask);
}

/// Gradiente linear que cobre a área na direção dada (180° = de cima para baixo)
pub fn gradiente(
    x: f32, y: f32, w: f32, h: f32, angulo: f32, c1: Color, c2: Color,
) -> Shader<'static> {
    let rad = angulo.to_radians();
    let (dx, dy) = (rad.sin(), -rad.cos());
    let meio = ((w * dx).abs() + (h * dy).abs()) / 2.0;
    let (cx, cy) = (x + w / 2.0, y + h / 2.0);
    let ini = Point::from_xy(cx - dx * meio, cy - dy * meio);
    let fim = Point::from_xy(cx + dx * meio, cy + dy * meio);
    LinearGradient::new(
        ini,
        fim,
        vec![GradientStop::new(0.0, c1), GradientStop::new(1.0, c2)],
        SpreadMode::Pad,
        Transform::identity(),
    )
    .unwrap_or(Shader::SolidColor(c1))
}

/// Caminho rápido para camadas retangulares sem cantos arredondados e com mistura normal:
/// cor sólida ou gradiente linear de duas cores, em pixels finais (x0..x1, y0..y1).
/// O tiny-skia sem SIMD de 256 bits é lento para áreas grandes; aqui é uma tabela de 256 cores
/// e mistura em inteiros. Para cor sólida, passe c1 == c2.
pub struct Faixa {
    pub x0: f32,
    pub y0: f32,
    pub x1: f32,
    pub y1: f32,
    /// t(px, py) = a*px + b*py + c, limitado a 0..1 (posição no gradiente)
    pub a: f32,
    pub b: f32,
    pub c: f32,
}

pub fn preencher_faixa(pm: &mut Pixmap, f: &Faixa, c1: Color, c2: Color) {
    let (w, h) = (pm.width() as i32, pm.height() as i32);
    let ix0 = (f.x0.floor() as i32).max(0);
    let iy0 = (f.y0.floor() as i32).max(0);
    let ix1 = (f.x1.ceil() as i32).min(w);
    let iy1 = (f.y1.ceil() as i32).min(h);
    if ix1 <= ix0 || iy1 <= iy0 {
        return;
    }
    // Tabela de cores pré-multiplicadas (0..255) ao longo do gradiente
    let mut tabela = [[0f32; 4]; 256];
    for (i, item) in tabela.iter_mut().enumerate() {
        let t = i as f32 / 255.0;
        let l = |a: f32, b: f32| a + (b - a) * t;
        let alfa = l(c1.alpha(), c2.alpha());
        *item = [l(c1.red(), c2.red()) * alfa * 255.0, l(c1.green(), c2.green()) * alfa * 255.0, l(c1.blue(), c2.blue()) * alfa * 255.0, alfa * 255.0];
    }
    let cobertura = |i: i32, a: f32, b: f32| ((i as f32 + 1.0).min(b) - (i as f32).max(a)).clamp(0.0, 1.0);
    let largura = w as usize;
    let dados = pm.data_mut();
    for py in iy0..iy1 {
        let cy = cobertura(py, f.y0, f.y1);
        let yc = py as f32 + 0.5;
        let linha = py as usize * largura * 4;
        for px in ix0..ix1 {
            let cob = cy * cobertura(px, f.x0, f.x1);
            if cob <= 0.0 {
                continue;
            }
            let t = (f.a * (px as f32 + 0.5) + f.b * yc + f.c).clamp(0.0, 1.0);
            let s = &tabela[(t * 255.0 + 0.5) as usize];
            let sa = s[3] * cob;
            if sa <= 0.0 {
                continue;
            }
            let inv = 1.0 - sa / 255.0;
            let o = linha + px as usize * 4;
            let d = &mut dados[o..o + 4];
            for k in 0..3 {
                d[k] = (s[k] * cob + d[k] as f32 * inv + 0.5).min(255.0) as u8;
            }
            d[3] = (sa + d[3] as f32 * inv + 0.5).min(255.0) as u8;
        }
    }
}

/// Coeficientes de t(px, py) para o gradiente que cobre (x, y, w, h) num ângulo, já em pixels finais
pub fn coef_gradiente(x: f32, y: f32, w: f32, h: f32, angulo: f32) -> (f32, f32, f32) {
    let rad = angulo.to_radians();
    let (dx, dy) = (rad.sin(), -rad.cos());
    let meio = ((w * dx).abs() + (h * dy).abs()) / 2.0;
    if meio <= 0.0 {
        return (0.0, 0.0, 0.0);
    }
    let (cx, cy) = (x + w / 2.0, y + h / 2.0);
    let (sx, sy) = (cx - dx * meio, cy - dy * meio);
    let comp = 2.0 * meio;
    // t = ((px - sx)*dx + (py - sy)*dy) / comp
    (dx / comp, dy / comp, -(sx * dx + sy * dy) / comp)
}

pub fn modo_mistura(nome: Option<&str>) -> BlendMode {
    match nome.unwrap_or("") {
        "multiply" => BlendMode::Multiply,
        "screen" => BlendMode::Screen,
        "overlay" => BlendMode::Overlay,
        "darken" => BlendMode::Darken,
        "lighten" => BlendMode::Lighten,
        "color-dodge" => BlendMode::ColorDodge,
        "color-burn" => BlendMode::ColorBurn,
        "hard-light" => BlendMode::HardLight,
        "soft-light" => BlendMode::SoftLight,
        "difference" => BlendMode::Difference,
        "exclusion" => BlendMode::Exclusion,
        "hue" => BlendMode::Hue,
        "saturation" => BlendMode::Saturation,
        "color" => BlendMode::Color,
        "luminosity" => BlendMode::Luminosity,
        _ => BlendMode::SourceOver,
    }
}

// ===========================================================================
// Desfoque (efeito "vidro"): três passadas de média móvel ≈ desfoque gaussiano
// ===========================================================================

/// Desfoca o que já está desenhado dentro de `caminho` (coordenadas em pixels finais).
/// `sigma` é o raio do blur(), como no filtro do canvas.
pub fn desfocar_regiao(pm: &mut Pixmap, caminho: &Path, sigma: f32) {
    if sigma <= 0.0 {
        return;
    }
    let b = caminho.bounds();
    let margem = (sigma * 2.0).ceil();
    let sx = (b.left() - margem).floor().max(0.0) as u32;
    let sy = (b.top() - margem).floor().max(0.0) as u32;
    let ex = ((b.right() + margem).ceil() as u32).min(pm.width());
    let ey = ((b.bottom() + margem).ceil() as u32).min(pm.height());
    if ex <= sx || ey <= sy {
        return;
    }
    let (sw, sh) = (ex - sx, ey - sy);
    let Some(mut copia) = pm.clone_rect(tiny_skia::IntRect::from_xywh(sx as i32, sy as i32, sw, sh).unwrap()) else {
        return;
    };
    for raio in caixas(sigma) {
        caixa_horizontal(copia.data_mut(), sw as usize, sh as usize, raio);
        caixa_vertical(copia.data_mut(), sw as usize, sh as usize, raio);
    }
    let Some(mut mask) = Mask::new(pm.width(), pm.height()) else { return };
    mask.fill_path(caminho, FillRule::Winding, true, Transform::identity());
    let paint = PixmapPaint { blend_mode: BlendMode::Source, ..PixmapPaint::default() };
    pm.draw_pixmap(sx as i32, sy as i32, copia.as_ref(), &paint, Transform::identity(), Some(&mask));
}

/// Raios das três médias móveis que aproximam um gaussiano de desvio `sigma`
fn caixas(sigma: f32) -> [usize; 3] {
    let n = 3.0;
    let w_ideal = (12.0 * sigma * sigma / n + 1.0).sqrt();
    let mut wl = w_ideal.floor() as i32;
    if wl % 2 == 0 {
        wl -= 1;
    }
    let wu = wl + 2;
    let m_ideal = (12.0 * sigma * sigma - n * (wl * wl) as f32 - 4.0 * n * wl as f32 - 3.0 * n) / (-4.0 * wl as f32 - 4.0);
    let m = m_ideal.round() as i32;
    let mut r = [0usize; 3];
    for (i, item) in r.iter_mut().enumerate() {
        let w = if (i as i32) < m { wl } else { wu };
        *item = ((w - 1) / 2).max(0) as usize;
    }
    r
}

/// Média móvel de raio `r` sobre `n` pixels RGBA, lidos de `src` com passo `passo` (em pixels)
/// a partir de `ini`; bordas repetem o pixel da ponta. Escreve de volta em `d`.
fn caixa_linha(d: &mut [u8], tmp: &mut Vec<[u32; 4]>, ini: usize, passo: usize, n: usize, r: usize) {
    tmp.clear();
    tmp.extend((0..n).map(|i| {
        let o = (ini + i * passo) * 4;
        [d[o] as u32, d[o + 1] as u32, d[o + 2] as u32, d[o + 3] as u32]
    }));
    let div = (2 * r + 1) as u32;
    let (primeiro, ultimo) = (tmp[0], tmp[n - 1]);
    let px = |i: isize| -> [u32; 4] {
        if i < 0 { primeiro } else if i as usize >= n { ultimo } else { tmp[i as usize] }
    };
    let mut soma = [0u32; 4];
    for i in -(r as isize)..=(r as isize) {
        let p = px(i);
        for k in 0..4 { soma[k] += p[k]; }
    }
    for i in 0..n {
        let o = (ini + i * passo) * 4;
        for k in 0..4 { d[o + k] = ((soma[k] + div / 2) / div) as u8; }
        let (entra, sai) = (px(i as isize + r as isize + 1), px(i as isize - r as isize));
        for k in 0..4 { soma[k] = soma[k] + entra[k] - sai[k]; }
    }
}

fn caixa_horizontal(d: &mut [u8], w: usize, h: usize, r: usize) {
    if r == 0 || w == 0 { return; }
    let mut tmp = Vec::with_capacity(w);
    for y in 0..h { caixa_linha(d, &mut tmp, y * w, 1, w, r); }
}

fn caixa_vertical(d: &mut [u8], w: usize, h: usize, r: usize) {
    if r == 0 || h == 0 { return; }
    let mut tmp = Vec::with_capacity(h);
    for x in 0..w { caixa_linha(d, &mut tmp, x, w, h, r); }
}

// ===========================================================================
// Imagens enviadas pela página (fundo e logos)
// ===========================================================================

/// Imagem com versões reduzidas pela metade, para reduzir sem serrilhado
pub struct Imagem {
    niveis: Vec<Pixmap>,
}

impl Imagem {
    /// `rgba`: pixels sem pré-multiplicação, como vêm de getImageData
    pub fn nova(largura: u32, altura: u32, rgba: &[u8]) -> Option<Imagem> {
        let mut dados = rgba.to_vec();
        for px in dados.chunks_exact_mut(4) {
            let a = px[3] as u32;
            if a < 255 {
                for c in &mut px[..3] {
                    *c = ((*c as u32 * a + 127) / 255) as u8;
                }
            }
        }
        let base = Pixmap::from_vec(dados, IntSize::from_wh(largura, altura)?)?;
        let mut niveis = vec![base];
        loop {
            let ult = niveis.last().unwrap();
            if ult.width() < 64 || ult.height() < 64 {
                break;
            }
            let Some(menor) = metade(ult) else { break };
            niveis.push(menor);
        }
        Some(Imagem { niveis })
    }

    pub fn largura(&self) -> f32 {
        self.niveis[0].width() as f32
    }
    pub fn altura(&self) -> f32 {
        self.niveis[0].height() as f32
    }

    /// Desenha a imagem no retângulo (x, y, w, h) do formato; `t` leva ao pixel final
    pub fn desenhar(&self, pm: &mut Pixmap, x: f32, y: f32, w: f32, h: f32, t: Transform) {
        let escala = (w / self.largura()) * t.sx;
        let mut nivel = 0;
        while nivel + 1 < self.niveis.len() && escala * (1 << nivel) as f32 * 2.0 < 1.0 {
            nivel += 1;
        }
        let img = &self.niveis[nivel];
        let (iw, ih) = (img.width() as f32, img.height() as f32);
        let local = Transform::from_row(w / iw, 0.0, 0.0, h / ih, x, y);
        let Some(rect) = Rect::from_xywh(x, y, w, h) else { return };
        let paint = Paint {
            shader: Pattern::new(img.as_ref(), SpreadMode::Pad, FilterQuality::Bicubic, 1.0, local),
            anti_alias: true,
            ..Paint::default()
        };
        pm.fill_rect(rect, &paint, t, None);
    }
}

fn metade(p: &Pixmap) -> Option<Pixmap> {
    let (w, h) = (p.width() / 2, p.height() / 2);
    let mut out = Pixmap::new(w, h)?;
    let (src, sw) = (p.data(), p.width() as usize);
    let dst = out.data_mut();
    for y in 0..h as usize {
        for x in 0..w as usize {
            for c in 0..4 {
                let s = |dx: usize, dy: usize| src[((y * 2 + dy) * sw + x * 2 + dx) * 4 + c] as u32;
                dst[(y * w as usize + x) * 4 + c] = ((s(0, 0) + s(1, 0) + s(0, 1) + s(1, 1) + 2) / 4) as u8;
            }
        }
    }
    Some(out)
}
