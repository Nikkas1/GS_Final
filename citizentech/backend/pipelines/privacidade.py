"""Mascaramento de dados pessoais (LGPD), com os mesmos padrões do Robô Cuidador (RPA).
Todo texto livre passa por aqui ANTES de ir para o LLM e antes de ser salvo."""
import re

PADROES = [
    ("[EMAIL]", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("[CPF]", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")),
    ("[CEP]", re.compile(r"\b\d{5}-\d{3}\b")),
    ("[TELEFONE]", re.compile(r"(?:\+?55\s?)?\(?\b\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b")),
    ("[NIS]", re.compile(r"\b\d{3}\.?\d{5}\.?\d{2}-?\d\b")),
]


def mascarar(texto: str) -> str:
    for marcador, padrao in PADROES:
        texto = padrao.sub(marcador, texto)
    return texto
