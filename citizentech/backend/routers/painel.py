from fastapi import APIRouter

from core.deps import RepoDep
from schemas.painel import Resumo

router = APIRouter(prefix="/painel", tags=["painel"])


@router.get("/resumo", response_model=Resumo, summary="Indicadores para o painel do cuidador")
def resumo(repo: RepoDep):
    return repo.resumo()
