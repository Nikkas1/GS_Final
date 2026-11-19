from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from core.deps import ModeloDep, SettingsDep
from pipelines.visao import classificar
from providers.modelo import ModeloIndisponivel
from schemas.visao import VisaoResposta

router = APIRouter(prefix="/visao", tags=["visão computacional"])

TIPOS = {"image/jpeg", "image/png"}
MAX_BYTES = 5 * 1024 * 1024


@router.post("/classificar", response_model=VisaoResposta,
             summary="Foto de calçada/muro → possível fissura (modelo do grupo)")
async def classificar_foto(modelo: ModeloDep, settings: SettingsDep, arquivo: UploadFile = File(...)):
    if arquivo.content_type not in TIPOS:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Envie uma imagem JPG ou PNG.")
    conteudo = await arquivo.read(MAX_BYTES + 1)
    if len(conteudo) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Imagem muito grande (máximo 5 MB).")
    try:
        # TensorFlow é bloqueante: roda numa thread para não travar o event loop
        return await run_in_threadpool(classificar, modelo, conteudo, settings.limiar_fissura)
    except ModeloIndisponivel:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Análise de imagem indisponível no momento.")
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não foi possível ler a imagem.")
