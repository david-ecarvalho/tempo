//! Formatos (dados/layouts-imagens.json) e dados de cada imagem, lidos do JSON enviado pela página.
use serde::Deserialize;

#[derive(Deserialize, Clone)]
pub struct Layout {
    pub largura: f32,
    pub altura: f32,
    #[serde(default)]
    pub cor_fundo: Option<String>,
    #[serde(default)]
    pub camadas: Vec<Camada>,
    #[serde(default)]
    pub selo: Option<Selo>,
    #[serde(default)]
    pub logos: Option<AreaLogos>,
    #[serde(default)]
    pub titulo: Option<AreaTitulo>,
    #[serde(default)]
    pub rodape: Option<AreaRodape>,
    #[serde(default)]
    pub qr: Option<Qr>,
}

#[derive(Deserialize, Clone)]
pub struct Camada {
    #[serde(default)]
    pub tipo: String,
    pub x: f32,
    pub y: f32,
    pub largura: f32,
    pub altura: f32,
    #[serde(default)]
    pub cor: Option<String>,
    #[serde(default)]
    pub alpha: Option<f32>,
    #[serde(default)]
    pub cor2: Option<String>,
    #[serde(default)]
    pub alpha2: Option<f32>,
    /// "para baixo", "para cima", "para direita", "para esquerda" ou um ângulo em graus
    #[serde(default)]
    pub direcao: Option<serde_json::Value>,
    #[serde(default)]
    pub raio: Option<f32>,
    #[serde(default)]
    pub desfoque: Option<f32>,
    #[serde(default)]
    pub mistura: Option<String>,
}

#[derive(Deserialize, Clone)]
pub struct Selo {
    pub x: f32,
    pub y: f32,
    pub altura: f32,
    pub fonte: f32,
    #[serde(default)]
    pub espaco_letras: f32,
    pub cor: String,
    pub cor_fundo: String,
    #[serde(default)]
    pub alpha_fundo: Option<f32>,
    pub margem: f32,
}

#[derive(Deserialize, Clone)]
pub struct AreaLogos {
    pub x: f32,
    pub y: f32,
    pub largura: f32,
    pub altura: f32,
    #[serde(default)]
    pub espaco: f32,
    #[serde(default)]
    pub alinhar: Option<String>,
}

#[derive(Deserialize, Clone)]
pub struct AreaTitulo {
    pub x: f32,
    pub y: f32,
    pub largura: f32,
    pub altura: f32,
    pub fonte_max: f32,
    pub fonte_min: f32,
    #[serde(default)]
    pub entrelinha: Option<f32>,
    pub cor: String,
    #[serde(default)]
    pub alinhar: Option<String>,
    #[serde(default)]
    pub vertical: Option<String>,
    #[serde(default)]
    pub max_linhas: Option<u32>,
}

#[derive(Deserialize, Clone)]
pub struct AreaRodape {
    pub x: f32,
    pub y: f32,
    pub largura: f32,
    pub altura: f32,
    pub fonte: f32,
    #[serde(default)]
    pub entrelinha: Option<f32>,
    pub cor: String,
    #[serde(default)]
    pub cor_destaque: Option<String>,
    #[serde(default)]
    pub alinhar: Option<String>,
    #[serde(default)]
    pub vertical: Option<String>,
}

#[derive(Deserialize, Clone)]
pub struct Qr {
    pub x: f32,
    pub y: f32,
    pub tamanho: f32,
    pub margem: f32,
    #[serde(default)]
    pub raio: Option<f32>,
    pub cor: String,
    pub cor_fundo: String,
    #[serde(default)]
    pub alpha_fundo: Option<f32>,
}

/// O que a pessoa preencheu. As imagens chegam antes, por `definir_imagem`, e aqui vêm só os nomes.
#[derive(Deserialize, Default)]
pub struct Dados {
    #[serde(default)]
    pub titulo: String,
    #[serde(default, rename = "linhasTitulo")]
    pub linhas_titulo: u32,
    #[serde(default)]
    pub selo: String,
    #[serde(default)]
    pub rodape: Vec<String>,
    #[serde(default)]
    pub link: String,
    #[serde(default)]
    pub fundo: Option<String>,
    #[serde(default = "cinquenta", rename = "focoX")]
    pub foco_x: f32,
    #[serde(default = "cinquenta", rename = "focoY")]
    pub foco_y: f32,
    #[serde(default)]
    pub logos: Vec<String>,
}

fn cinquenta() -> f32 {
    50.0
}
