from fastapi import APIRouter

from core.deps import ModeloDep, SettingsDep

router = APIRouter(tags=["saúde"])


@router.get("/health", summary="Liveness (usado pelo healthcheck do Docker)")
def health():
    return {"status": "ok"}


@router.get("/health/ready", summary="O que está disponível agora")
def ready(settings: SettingsDep, modelo: ModeloDep):
    return {
        "status": "ok",
        "llm": settings.llm_provider if settings.llm_configurado else "sem_chave",
        "visao": modelo.disponivel,
    }
