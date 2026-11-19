from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Query, status

from core.deps import RepoDep, SettingsDep
from pipelines import eventos as pipeline
from schemas.evento import ClasseSom, EventoRegistrado, EventoSom, Feedback

router = APIRouter(prefix="/eventos", tags=["eventos OuviAí"])


@router.post("", response_model=list[EventoRegistrado], status_code=status.HTTP_201_CREATED,
             summary="Recebe detecções do celular (evento_som do contrato de integração)")
def receber(eventos: Annotated[list[EventoSom], Body(min_length=1, max_length=200)],
            repo: RepoDep, settings: SettingsDep):
    salvos = []
    for e in sorted(eventos, key=lambda x: x.momento):
        repeticoes = repo.eventos_recentes(e.dispositivo, e.classe.value, e.momento - pipeline.JANELA_REPETICAO)
        salvos += repo.criar_eventos([pipeline.classificar(e, settings.confianca_minima_evento, repeticoes)])
    return salvos


@router.get("", response_model=list[EventoRegistrado], summary="Lista eventos (mais recentes primeiro)")
def listar(repo: RepoDep,
           classe: Annotated[list[ClasseSom] | None, Query()] = None,
           confianca_min: Annotated[float, Query(ge=0, le=1)] = 0.0,
           desde: datetime | None = None,
           limite: Annotated[int, Query(ge=1, le=1000)] = 500):
    classes = [c.value for c in classe] if classe else None
    return repo.listar_eventos(classes, confianca_min, desde, limite)


@router.patch("/{evento_id}/feedback", response_model=EventoRegistrado,
              summary="Human-in-the-loop: o aviso estava certo?")
def feedback(evento_id: int, fb: Feedback, repo: RepoDep):
    e = repo.feedback_evento(evento_id, fb.acertou)
    if e is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")
    return e
