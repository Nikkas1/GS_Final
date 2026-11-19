"""Dependências injetadas nos endpoints com Depends().

Os objetos caros (cliente do LLM, conexão SQLite, modelo de visão) são criados
uma vez no lifespan da aplicação e guardados em app.state. Nos testes, basta
trocar com app.dependency_overrides, sem monkeypatch em módulo.
"""
from typing import Annotated

from fastapi import Depends, Request

from core.config import Settings, get_settings
from providers.llm import LLM
from providers.modelo import ModeloFissura
from providers.repositorio import Repositorio


def get_repo(request: Request) -> Repositorio:
    return request.app.state.repo


def get_llm(request: Request) -> LLM:
    return request.app.state.llm


def get_modelo(request: Request) -> ModeloFissura:
    return request.app.state.modelo


SettingsDep = Annotated[Settings, Depends(get_settings)]
RepoDep = Annotated[Repositorio, Depends(get_repo)]
LLMDep = Annotated[LLM, Depends(get_llm)]
ModeloDep = Annotated[ModeloFissura, Depends(get_modelo)]
