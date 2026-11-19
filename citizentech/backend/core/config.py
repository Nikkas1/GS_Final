"""Configuração lida das variáveis de ambiente (ou do .env), validada pelo Pydantic.

Nada de os.getenv espalhado pelo código: quem precisa de configuração recebe
um Settings via Depends(get_settings).
"""
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # LLM
    llm_provider: str = Field("anthropic", description="anthropic ou simulado (demonstração sem chave)")
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5-5"
    llm_timeout_s: float = 30.0

    # API
    allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:8501"]
    db_path: Path = Path("dados/ouviai.db")
    seed_demo: bool = True
    eventos_demo_csv: Path = Path(__file__).resolve().parents[1] / "dados" / "eventos_demo.csv"

    # OuviAí: abaixo disso a detecção é "incerta" e não vira alerta (mesmo valor do robô RPA)
    confianca_minima_evento: float = 0.60

    # Visão computacional (opcional)
    model_path: Path = Path("models/modelo.keras")
    limiar_fissura: float = 0.5

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _origens(cls, v):
        if isinstance(v, str):
            v = [o.strip() for o in v.split(",") if o.strip()]
        if "*" in v:
            raise ValueError("CORS com '*' não é permitido; liste as origens.")
        return v

    @property
    def llm_configurado(self) -> bool:
        return self.llm_provider == "simulado" or bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
