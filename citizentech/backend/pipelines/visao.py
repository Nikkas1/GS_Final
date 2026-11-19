from providers.modelo import ModeloFissura
from schemas.visao import VisaoResposta

AVISO = ("Resultado de apoio à triagem. A presença de fissura na imagem não indica "
         "a gravidade do dano nem a segurança estrutural: encaminhe para vistoria profissional.")


def classificar(modelo: ModeloFissura, imagem_bytes: bytes, limiar: float) -> VisaoResposta:
    p = modelo.prever(imagem_bytes)
    return VisaoResposta(possivel_fissura=p >= limiar, confianca=p, limiar=limiar, aviso=AVISO)
