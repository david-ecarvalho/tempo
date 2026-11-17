"""Modo online do editor (servidor.py --online): login de voluntários e publicação pelo git.

Sem --online nada disto é usado e o editor continua só no computador local, como antes.

Login
- Cada voluntário tem usuário e senha em privado/usuarios.json, na raiz do repositório (fora do git e fora da pasta
  que o site serve), com a senha guardada só como hash
  PBKDF2-SHA256 (200 mil voltas, sal próprio). Para criar, trocar a senha ou tirar alguém:
      python scripts/usuarios.py adicionar <usuario>     (pergunta a senha)
      python scripts/usuarios.py remover <usuario>
      python scripts/usuarios.py listar
- Ao entrar, o servidor guarda uma sessão na memória e manda o cookie "tc_sessao" (HttpOnly, Secure, SameSite=Strict),
  que vale 12 horas. Reiniciar o servidor desfaz todas as sessões (todo mundo entra de novo).
- 5 senhas erradas seguidas do mesmo endereço travam o login desse endereço por 10 minutos.

Publicação
- Depois de salvar, apagar ou enviar imagem, o servidor faz "git add" do conteúdo, um commit com o nome de quem
  editou e "git push" para o ramo configurado (--ramo, padrão: o ramo atual). O workflow do GitHub publica o site.
- Os commits são enfileirados numa thread só; se o push falhar (sem rede, conflito), tenta de novo no próximo
  salvamento e o erro aparece no terminal.
"""
import base64
import hashlib
import hmac
import json
import secrets
import subprocess
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQ_USUARIOS = RAIZ.parent / "privado" / "usuarios.json"
VOLTAS = 200_000
SESSAO_SEGUNDOS = 12 * 3600
TENTATIVAS, TRAVA_SEGUNDOS = 5, 600
COOKIE = "tc_sessao"


# ---------------- usuários ----------------

def _hash(senha, sal):
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, VOLTAS)


def ler_usuarios(arquivo=ARQ_USUARIOS):
    try:
        return json.loads(Path(arquivo).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def gravar_usuario(usuario, senha, arquivo=ARQ_USUARIOS):
    usuarios = ler_usuarios(arquivo)
    sal = secrets.token_bytes(16)
    usuarios[usuario] = {"sal": base64.b64encode(sal).decode(), "hash": base64.b64encode(_hash(senha, sal)).decode()}
    Path(arquivo).parent.mkdir(parents=True, exist_ok=True)
    Path(arquivo).write_text(json.dumps(usuarios, ensure_ascii=False, indent=1), encoding="utf-8")


def remover_usuario(usuario, arquivo=ARQ_USUARIOS):
    usuarios = ler_usuarios(arquivo)
    if usuarios.pop(usuario, None) is None:
        return False
    Path(arquivo).write_text(json.dumps(usuarios, ensure_ascii=False, indent=1), encoding="utf-8")
    return True


def conferir_senha(usuario, senha, arquivo=ARQ_USUARIOS):
    dados = ler_usuarios(arquivo).get(usuario)
    if not dados:
        _hash(senha, b"x" * 16)  # mesmo tempo de resposta para usuário que não existe
        return False
    esperado = base64.b64decode(dados["hash"])
    return hmac.compare_digest(_hash(senha, base64.b64decode(dados["sal"])), esperado)


# ---------------- sessões ----------------

class Sessoes:
    def __init__(self):
        self._trava = threading.Lock()
        self._sessoes = {}   # token -> (usuario, vence_em)
        self._erros = {}     # endereço -> (quantas, desde)

    def travado(self, endereco):
        with self._trava:
            n, desde = self._erros.get(endereco, (0, 0))
            if n >= TENTATIVAS and time.time() - desde < TRAVA_SEGUNDOS:
                return True
            if n >= TENTATIVAS:
                self._erros.pop(endereco, None)
            return False

    def errou(self, endereco):
        with self._trava:
            n, desde = self._erros.get(endereco, (0, time.time()))
            self._erros[endereco] = (n + 1, desde if n else time.time())

    def criar(self, usuario, endereco):
        token = secrets.token_urlsafe(32)
        with self._trava:
            self._erros.pop(endereco, None)
            self._sessoes[token] = (usuario, time.time() + SESSAO_SEGUNDOS)
        return token

    def usuario(self, token):
        if not token:
            return None
        with self._trava:
            par = self._sessoes.get(token)
            if not par:
                return None
            if time.time() > par[1]:
                self._sessoes.pop(token, None)
                return None
            return par[0]

    def encerrar(self, token):
        with self._trava:
            self._sessoes.pop(token, None)


def token_do_cookie(cabecalho):
    for parte in (cabecalho or "").split(";"):
        nome, _, valor = parte.strip().partition("=")
        if nome == COOKIE:
            return valor
    return None


def cookie_sessao(token, apagar=False):
    idade = 0 if apagar else SESSAO_SEGUNDOS
    return f"{COOKIE}={'' if apagar else token}; Path=/; Max-Age={idade}; HttpOnly; Secure; SameSite=Strict"


# ---------------- git ----------------

class Publicador:
    """Commit e push em fila, um de cada vez, a partir da pasta do repositório."""

    def __init__(self, repo, ramo=None):
        self.repo = Path(repo)
        self.ramo = ramo
        self._trava = threading.Lock()

    def _git(self, *args, checar=True):
        r = subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True, timeout=120)
        if checar and r.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
        return r

    def publicar(self, mensagem, usuario):
        threading.Thread(target=self._publicar, args=(mensagem, usuario), daemon=True).start()

    def _publicar(self, mensagem, usuario):
        with self._trava:
            try:
                self._git("add", "-A", "site/conteudo", "site/imagens", "site/arquivos", "site/dados")
                if self._git("diff", "--cached", "--quiet", checar=False).returncode != 0:
                    self._git("-c", f"user.name={usuario} (editor online)", "-c", "user.email=editor@tempocontinuum",
                              "commit", "-q", "-m", f"{mensagem} (por {usuario}, pelo editor online)")
                ramo = self.ramo or self._git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
                self._git("pull", "-q", "--rebase", "origin", ramo, checar=False)
                self._git("push", "-q", "origin", f"HEAD:{ramo}")
                print(f"  [git] publicado: {mensagem} (por {usuario})", flush=True)
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
                print(f"  [git] não publiquei agora (tento de novo no próximo salvamento): {e}", flush=True)
