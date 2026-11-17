"""Usuários do editor online (servidor.py --online). Ficam em privado/usuarios.json, fora do git.

Uso:  python scripts/usuarios.py adicionar <usuario>   (cria ou troca a senha; a senha é pedida sem aparecer)
      python scripts/usuarios.py remover <usuario>
      python scripts/usuarios.py listar
"""
import getpass
import re
import sys

import online


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("adicionar", "remover", "listar"):
        print(__doc__)
        sys.exit(1)
    acao = sys.argv[1]
    if acao == "listar":
        for u in sorted(online.ler_usuarios()):
            print(u)
        return
    if len(sys.argv) < 3 or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,31}", sys.argv[2].lower()):
        sys.exit("Usuário: de 2 a 32 letras minúsculas, números, ponto, hífen ou sublinhado.")
    usuario = sys.argv[2].lower()
    if acao == "remover":
        print("Removido." if online.remover_usuario(usuario) else "Esse usuário não existe.")
        return
    senha = getpass.getpass("Senha (mínimo 10 caracteres): ")
    if len(senha) < 10 or senha != getpass.getpass("Repita a senha: "):
        sys.exit("Senha curta demais ou diferente nas duas vezes. Nada mudou.")
    online.gravar_usuario(usuario, senha)
    print(f"Usuário {usuario} pronto. Quem estava logado com ele continua até sair ou o servidor reiniciar.")


if __name__ == "__main__":
    main()
