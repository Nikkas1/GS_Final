"""API do OuviAí Cidade (CitizenTech).

uvicorn main:app --reload        documentação interativa em http://localhost:8000/docs
"""
import csv
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import get_settings
from pipelines import eventos as pipeline_eventos
from providers.llm import ErroProvedor, criar_llm
from providers.modelo import ModeloFissura
from providers.repositorio import Repositorio
from routers import eventos, painel, pedidos, saude, visao
from schemas.evento import EventoSom

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ouviai")


def carregar_demo(repo: Repositorio, settings) -> int:
    """Semana de demonstração: os mesmos eventos sintéticos que o Robô Cuidador (RPA) consome."""
    if repo.contar_eventos() > 0 or not settings.eventos_demo_csv.exists():
        return 0
    with open(settings.eventos_demo_csv, encoding="utf-8") as f:
        linhas = [EventoSom.model_validate(l) for l in csv.DictReader(f)]
    for e in sorted(linhas, key=lambda x: x.momento):
        rep = repo.eventos_recentes(e.dispositivo, e.classe.value, e.momento - pipeline_eventos.JANELA_REPETICAO)
        repo.criar_eventos([pipeline_eventos.classificar(e, settings.confianca_minima_evento, rep)])
    return len(linhas)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.repo = Repositorio(settings.db_path)
    app.state.llm = criar_llm(settings.llm_provider, settings.anthropic_api_key, settings.llm_model, settings.llm_timeout_s)
    app.state.modelo = ModeloFissura(settings.model_path)
    if settings.seed_demo:
        n = carregar_demo(app.state.repo, settings)
        if n:
            log.info("semana de demonstração carregada: %d eventos", n)
    if not settings.llm_configurado:
        log.warning("ANTHROPIC_API_KEY ausente: /pedidos vai responder 503 (use LLM_PROVIDER=simulado para demonstrar)")
    yield
    await app.state.llm.fechar()
    app.state.repo.fechar()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="OuviAí Cidade · CitizenTech API",
        version="2.0.0",
        description="Triagem de pedidos de ajuda com LLM (saída Pydantic) e avisos visuais do classificador de sons OuviAí.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def tempo(request: Request, call_next):
        inicio = time.perf_counter()
        resp = await call_next(request)
        ms = (time.perf_counter() - inicio) * 1000
        resp.headers["X-Tempo-ms"] = f"{ms:.0f}"
        log.info("%s %s %s %.0fms", request.method, request.url.path, resp.status_code, ms)
        return resp

    @app.exception_handler(RequestValidationError)
    async def validacao(request: Request, exc: RequestValidationError):
        campos = sorted({str(e["loc"][-1]) for e in exc.errors()})
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            content={"detail": "Confira os campos enviados.", "campos": campos})

    @app.exception_handler(ErroProvedor)
    async def erro_llm(request: Request, exc: ErroProvedor):
        log.error("falha no provedor de LLM: %s", exc)   # detalhe técnico só no log
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY,
                            content={"detail": "Não foi possível analisar o pedido agora."})

    app.include_router(saude.router)
    for r in (pedidos.router, eventos.router, painel.router, visao.router):
        app.include_router(r, prefix="/v1")
    return app


app = create_app()
