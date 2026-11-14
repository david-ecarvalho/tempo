//! Testes do motor fora do navegador: cargo test
use motor_imagens::Motor;

fn layouts() -> Vec<serde_json::Value> {
    let texto = std::fs::read_to_string("../site/dados/layouts-imagens.json").unwrap();
    let v: serde_json::Value = serde_json::from_str(&texto).unwrap();
    v["layouts"].as_array().unwrap().clone()
}

const DADOS: &str = r#"{"titulo":"Escreva aqui o título: ele se ajusta sozinho à área demarcada","selo":"Exclusivo",
"rodape":["tempocontinuum.com.br","Leia a matéria completa"],"link":"https://tempocontinuum.com.br/materia.html?id=teste"}"#;

#[test]
fn todos_os_formatos_montam_e_o_qr_le_o_link() {
    let motor = Motor::new();
    for l in layouts() {
        let nome = l["nome"].as_str().unwrap().to_string();
        let r = motor.renderizar(&l.to_string(), DADOS, 1.0, false).unwrap_or_else(|_| panic!("{nome}"));
        assert_eq!(r.largura(), l["largura"].as_u64().unwrap() as u32);
        let rel: serde_json::Value = serde_json::from_str(&r.relatorio()).unwrap();
        assert!(rel["avisos"].as_array().unwrap().is_empty(), "{nome}: {rel}");
        assert!(!rel["titulo"]["cortado"].as_bool().unwrap(), "{nome}");

        // Recorta o QR e lê com um decodificador independente
        let q = &l["qr"];
        let (qx, qy, qt) = (q["x"].as_u64().unwrap() as usize, q["y"].as_u64().unwrap() as usize, q["tamanho"].as_u64().unwrap() as usize);
        let (w, px) = (r.largura() as usize, r.pixels());
        let cinza = |x: usize, y: usize| { let o = ((qy + y) * w + qx + x) * 4; ((px[o] as u32 + px[o + 1] as u32 + px[o + 2] as u32) / 3) as u8 };
        let mut img = rqrr::PreparedImage::prepare_from_greyscale(qt, qt, |x, y| cinza(x, y));
        let grades = img.detect_grids();
        assert_eq!(grades.len(), 1, "{nome}: QR não encontrado");
        let (_, conteudo) = grades[0].decode().unwrap();
        assert_eq!(conteudo, "https://tempocontinuum.com.br/materia.html?id=teste", "{nome}");
    }
}

#[test]
fn titulo_longo_demais_e_cortado_com_reticencias() {
    let motor = Motor::new();
    let l = &layouts()[0];
    let titulo = "palavra ".repeat(400);
    let dados = serde_json::json!({ "titulo": titulo }).to_string();
    let r = motor.renderizar(&l.to_string(), &dados, 0.5, false).unwrap();
    let rel: serde_json::Value = serde_json::from_str(&r.relatorio()).unwrap();
    assert!(rel["titulo"]["cortado"].as_bool().unwrap());
    assert_eq!(rel["titulo"]["linhas"].as_u64().unwrap(), 6);
}

#[test]
fn link_longo_demais_vira_aviso() {
    let motor = Motor::new();
    let l = &layouts()[0];
    let dados = serde_json::json!({ "link": "x".repeat(5000) }).to_string();
    let r = motor.renderizar(&l.to_string(), &dados, 0.5, false).unwrap();
    assert!(r.relatorio().contains("longo demais para o QR"));
}
