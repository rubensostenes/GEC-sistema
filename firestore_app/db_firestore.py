"""Camada de acesso ao Firestore — equivalente ao db.py (SQLite) do app atual.

Autenticação: Admin SDK, via uma conta de serviço (mesma ideia do
netlify-firestore-poc, mas usada aqui pelo servidor Flask, não por uma
função serverless). Nunca comitar a chave — ela é lida de um arquivo local
apontado por GOOGLE_APPLICATION_CREDENTIALS, que fica de fora do git
(ver .gitignore).
"""
import os

import firebase_admin
from firebase_admin import credentials, firestore

_app = None


def get_db():
    """Devolve o client do Firestore. Cria a conexão uma única vez (o SDK já
    cuida de pool de conexões internamente — diferente do SQLite, não precisa
    abrir/fechar por requisição)."""
    global _app
    if _app is None:
        caminho_credencial = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not caminho_credencial:
            raise RuntimeError(
                "Defina GOOGLE_APPLICATION_CREDENTIALS apontando para o .json "
                "da conta de serviço antes de iniciar o app (nunca comite esse arquivo)."
            )
        cred = credentials.Certificate(caminho_credencial)
        _app = firebase_admin.initialize_app(cred)
    return firestore.client()


def proximo_numero(tipo: str) -> str:
    """Gera um número sequencial (equivalente ao AUTOINCREMENT usado pra
    numerar OS, pedidos, requisições etc.), via transação atômica num
    documento contador — Firestore não tem sequência nativa.

    `tipo` é a chave do contador, ex: "ordem_servico", "pedido_compra".
    """
    db = get_db()
    ref = db.collection("contadores").document(tipo)

    @firestore.transactional
    def _incrementar(transacao):
        snap = ref.get(transaction=transacao)
        atual = (snap.get("valor") if snap.exists else 0) or 0
        novo = atual + 1
        transacao.set(ref, {"valor": novo}, merge=True)
        return novo

    transacao = db.transaction()
    numero = _incrementar(transacao)
    return str(numero)
