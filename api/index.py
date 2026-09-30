"""Entrypoint do Vercel (Python Serverless Function / WSGI).

O Vercel importa este módulo e usa a variável `app` como aplicação WSGI.
Todas as rotas do vercel.json apontam pra cá.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from app import app  # noqa: E402,F401  (o Vercel procura `app` neste módulo)
