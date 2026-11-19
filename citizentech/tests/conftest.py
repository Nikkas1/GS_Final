import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from core.config import get_settings  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    """API completa (com lifespan) num banco temporário e com o LLM simulado: sem chave e sem internet."""
    monkeypatch.setenv("LLM_PROVIDER", "simulado")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:8501")
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "nao_existe.keras"))
    get_settings.cache_clear()
    from main import create_app
    app = create_app()
    with TestClient(app) as c:
        c.app_ref = app
        yield c
    get_settings.cache_clear()


class LLMFalso:
    """Devolve as respostas da lista, uma por chamada, e guarda o que recebeu."""
    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.recebido = []

    async def estruturar(self, system, usuario, schema):
        self.recebido.append(usuario)
        r = self.respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    async def fechar(self):
        pass
