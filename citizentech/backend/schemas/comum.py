from typing import Annotated

from pydantic import BeforeValidator, Field


def _cortar(limite: int):
    """O LLM às vezes passa alguns caracteres do limite. Cortar é melhor que
    devolver erro ao cidadão por causa de um resumo 5 caracteres maior."""
    def f(v):
        return v.strip()[:limite] if isinstance(v, str) else v
    return BeforeValidator(f)


def TextoCurto(limite: int, descricao: str):
    return Annotated[str, _cortar(limite), Field(min_length=1, max_length=limite, description=descricao)]
